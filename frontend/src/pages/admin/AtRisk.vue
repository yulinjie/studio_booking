<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const items = ref([])
const level = ref('all')
const minTotal = ref(1)
const selected = ref([])
const couponTemplates = ref([])
const loading = ref(false)

const showGrant = ref(false)
const grantForm = ref({ template_id: null })

async function load() {
  loading.value = true
  try {
    items.value = await api.get('/admin/at-risk-members', {
      params: { level: level.value, min_total: minTotal.value },
    })
    if (!couponTemplates.value.length) {
      couponTemplates.value = await api.get('/admin/coupon-templates')
    }
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

const stats = computed(() => {
  const s = { warning: 0, at_risk: 0, lost: 0 }
  for (const m of items.value) s[m.risk_level] = (s[m.risk_level] || 0) + 1
  return s
})

const RISK_STYLE = {
  warning: { bg: '#FAEEDE', color: '#A4836B', label: '即将流失', icon: '⚠' },
  at_risk: { bg: '#F2DDD3', color: '#A4654E', label: '高风险',   icon: '⚡' },
  lost:    { bg: '#EAD5D5', color: '#7A5A5A', label: '已流失',   icon: '✗' },
}

function openGrant() {
  if (!selected.value.length) return ElMessage.warning('先勾选会员')
  if (!couponTemplates.value.length) return ElMessage.warning('先去"优惠券"页创建一个挽回券模板')
  grantForm.value = { template_id: couponTemplates.value[0]?.id }
  showGrant.value = true
}

async function doGrant() {
  try {
    const r = await api.post('/admin/coupons/grant', {
      template_id: grantForm.value.template_id,
      member_ids: selected.value.map(m => m.id),
    })
    ElMessage.success(`已发出 ${r.granted} 张挽回券`)
    showGrant.value = false
    selected.value = []
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function getRowKey(row) { return row.id }
function handleSelectionChange(rows) { selected.value = rows }

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>流失预警</h2>
        <div class="sub">{{ items.length }} 位会员需要关注</div>
      </div>
    </div>

    <!-- 风险分布卡 -->
    <div class="risk-cards">
      <div
v-for="(meta, key) in RISK_STYLE" :key="key" class="risk-card"
           :class="{ active: level === key }"
           :style="{ background: meta.bg, color: meta.color }"
           @click="level = (level === key ? 'all' : key); load()">
        <div class="rc-icon">{{ meta.icon }}</div>
        <div class="rc-num">{{ stats[key] || 0 }}</div>
        <div class="rc-label">{{ meta.label }}</div>
        <div class="rc-range">
          {{ key === 'warning' ? '15-29 天' : key === 'at_risk' ? '30-59 天' : '60+ 天' }}
        </div>
      </div>
    </div>

    <el-card>
      <div class="actions">
        <el-radio-group v-model="level" size="default" @change="load">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="warning">即将流失</el-radio-button>
          <el-radio-button value="at_risk">高风险</el-radio-button>
          <el-radio-button value="lost">已流失</el-radio-button>
        </el-radio-group>
        <span style="font-size: 12px; color: #888; margin-left: 12px">
          至少上过 <el-input-number v-model="minTotal" :min="0" :step="1" size="small" style="width: 80px" @change="load" /> 节
        </span>
        <div style="flex: 1"></div>
        <el-button type="primary" :disabled="!selected.length" @click="openGrant">
          🎟 给选中 {{ selected.length }} 人发挽回券
        </el-button>
      </div>

      <el-table
v-loading="loading" :data="items" :row-key="getRowKey"
                empty-text="所有会员状态正常 ✨" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="风险" width="120">
          <template #default="{ row }">
            <span class="risk-tag" :style="{ background: RISK_STYLE[row.risk_level]?.bg, color: RISK_STYLE[row.risk_level]?.color }">
              {{ RISK_STYLE[row.risk_level]?.icon }} {{ RISK_STYLE[row.risk_level]?.label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="距今未上课" width="120">
          <template #default="{ row }">
            <b>{{ row.days_inactive >= 9999 ? '— —' : row.days_inactive + ' 天' }}</b>
          </template>
        </el-table-column>
        <el-table-column label="最后上课" width="140">
          <template #default="{ row }">
            {{ row.last_attended_at ? dayjs(row.last_attended_at).format('YYYY-MM-DD') : '— —' }}
          </template>
        </el-table-column>
        <el-table-column prop="total_attended" label="累计课次" width="100" />
        <el-table-column prop="active_cards" label="在用卡" width="80" />
        <el-table-column label="标签" min-width="120">
          <template #default="{ row }">
            <span v-if="row.tags" style="font-size: 11px; color: #888">{{ row.tags }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <router-link :to="`/admin/members/${row.id}`">
              <el-button size="small" link type="primary">详情</el-button>
            </router-link>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showGrant" title="发挽回券" width="450px">
      <el-form label-width="100px">
        <el-form-item label="券模板">
          <el-select v-model="grantForm.template_id" style="width: 100%" placeholder="选一张挽回用的优惠券">
            <el-option v-for="t in couponTemplates" :key="t.id" :label="`${t.name} ${t.value}元（${t.type}）`" :value="t.id" />
          </el-select>
          <div style="font-size: 11px; color: #888; margin-top: 4px">
            没有合适的？去「优惠券」页创建一个"挽回券"模板（如满 100 减 50）
          </div>
        </el-form-item>
        <el-form-item label="收件人">
          <div class="recipients">
            <span v-for="m in selected.slice(0, 8)" :key="m.id" class="r-chip">{{ m.name }}</span>
            <span v-if="selected.length > 8" class="r-chip">+{{ selected.length - 8 }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGrant = false">取消</el-button>
        <el-button type="primary" @click="doGrant">确认发放（{{ selected.length }} 人）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }

.risk-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0 18px; }
.risk-card {
  border-radius: var(--ys-radius);
  padding: 16px 18px;
  cursor: pointer;
  transition: all 0.18s;
  border: 1px solid transparent;
  position: relative;
}
.risk-card:hover { transform: translateY(-2px); box-shadow: var(--ys-shadow); }
.risk-card.active { border-color: currentColor; box-shadow: var(--ys-shadow); }
.rc-icon { font-size: 16px; }
.rc-num { font-size: 28px; font-weight: 300; margin-top: 4px; font-variant-numeric: tabular-nums; }
.rc-label { font-size: 13px; letter-spacing: 1px; opacity: 0.85; }
.rc-range { font-size: 11px; opacity: 0.7; margin-top: 2px; }

.actions { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.risk-tag { font-size: 11px; padding: 3px 10px; border-radius: 10px; letter-spacing: 0.5px; white-space: nowrap; }
.recipients { display: flex; flex-wrap: wrap; gap: 6px; }
.r-chip { font-size: 12px; background: var(--ys-bg-soft); padding: 3px 10px; border-radius: 4px; }
</style>

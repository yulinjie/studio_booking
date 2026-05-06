<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const members = ref([])
const couponTemplates = ref([])
const loading = ref(false)
const selectedTemplate = ref(null)

async function load() {
  loading.value = true
  try {
    const [m, c] = await Promise.all([
      api.get('/admin/birthday/this-month'),
      api.get('/admin/coupon-templates'),
    ])
    members.value = m
    couponTemplates.value = c.filter(t => t.is_active)
    // 自动选名字含'生日'的
    const bt = couponTemplates.value.find(t => t.name.includes('生日'))
    selectedTemplate.value = bt?.id || couponTemplates.value[0]?.id
  } finally { loading.value = false }
}

const stats = computed(() => ({
  total: members.value.length,
  granted: members.value.filter(m => m.coupon_granted_year).length,
  pending: members.value.filter(m => !m.coupon_granted_year).length,
}))

async function runBatch() {
  if (!selectedTemplate.value) return ElMessage.warning('选择一张券模板')
  const tmpl = couponTemplates.value.find(t => t.id === selectedTemplate.value)
  if (!tmpl.name.includes('生日')) {
    try {
      await ElMessageBox.confirm(
        `选中的模板"${tmpl.name}"不含'生日'字样，确认要用它做生日券吗？`,
        '提示', { type: 'warning' },
      )
    } catch { return }
  }
  try {
    const r = await api.post('/admin/birthday/run', { template_id: selectedTemplate.value })
    ElMessage.success(`本月寿星 ${r.candidates} 人 · 跳过已发 ${r.skipped} 人 · 实际发出 ${r.granted} 张`)
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

const monthName = computed(() => dayjs().format('M 月'))
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>生日礼遇</h2>
        <div class="sub">{{ monthName }}寿星 · 一键群发生日券</div>
      </div>
    </div>

    <!-- 三联数字 -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">本月寿星</div>
        <div class="kpi-value">{{ stats.total }}</div>
      </div>
      <div class="kpi-card kpi-accent">
        <div class="kpi-label">待发券</div>
        <div class="kpi-value">{{ stats.pending }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已发出</div>
        <div class="kpi-value">{{ stats.granted }}</div>
      </div>
    </div>

    <el-card style="margin-bottom: 16px">
      <template #header>
        <b>群发生日券</b>
      </template>
      <div class="run-row">
        <el-select v-model="selectedTemplate" placeholder="选生日券模板" style="width: 320px">
          <el-option v-for="t in couponTemplates" :key="t.id"
                     :label="`${t.name} ${t.value}元（${t.type}）`" :value="t.id" />
        </el-select>
        <el-button type="primary" :disabled="!stats.pending" @click="runBatch">
          🎂 给 {{ stats.pending }} 人发券
        </el-button>
      </div>
      <el-alert type="info" show-icon :closable="false" style="margin-top: 14px">
        重复执行不会重复发：今年已收到此模板生日券的会员会被自动跳过。<br>
        建议先在「优惠券」页创建一张名为'生日券'的模板（如满 200 减 50）。
      </el-alert>
    </el-card>

    <el-card>
      <template #header>
        <b>{{ monthName }}寿星名单</b>
      </template>

      <el-table :data="members" v-loading="loading" empty-text="本月暂无寿星 🎂">
        <el-table-column label="" width="50">
          <template #default="{ row }">
            <span class="cake">🎂</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column label="生日" width="120">
          <template #default="{ row }">
            {{ dayjs(row.birthday).format('M月D日') }}
          </template>
        </el-table-column>
        <el-table-column label="年龄" width="80">
          <template #default="{ row }">{{ row.age }}</template>
        </el-table-column>
        <el-table-column label="本年券">
          <template #default="{ row }">
            <el-tag v-if="row.coupon_granted_year" type="success" size="small">已发</el-tag>
            <el-tag v-else type="warning" size="small">待发</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <router-link :to="`/admin/members/${row.id}`">
              <el-button size="small" link type="primary">详情</el-button>
            </router-link>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 16px 0 18px;
}
.kpi-card {
  background: var(--ys-bg-card);
  border: 1px solid var(--ys-line);
  border-radius: var(--ys-radius);
  padding: 18px 20px;
}
.kpi-card::before {
  content: ''; position: absolute; inset: 0 0 auto 0; height: 2px;
  background: linear-gradient(90deg, var(--ys-primary), transparent); opacity: 0.5;
}
.kpi-accent { background: linear-gradient(135deg, var(--ys-primary-bg) 0%, var(--ys-bg-card) 100%); }
.kpi-label { font-size: 12px; color: var(--ys-text-muted); letter-spacing: 2px; }
.kpi-value { font-size: 32px; font-weight: 300; color: var(--ys-text); margin-top: 6px; font-variant-numeric: tabular-nums; }

.run-row { display: flex; align-items: center; gap: 12px; }
.cake { font-size: 18px; }
</style>

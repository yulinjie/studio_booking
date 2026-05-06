<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
import dayjs from 'dayjs'

const tab = ref('templates')
const templates = ref([])
const issued = ref([])
const showCreate = ref(false)
const form = ref({})
const showGrant = ref(false)
const grantForm = ref({})
const members = ref([])

const TYPES = [
  { value: 'discount', label: '满减券（满 X 减 Y）' },
  { value: 'percent', label: '折扣券（X%）' },
  { value: 'cash', label: '现金券（直接抵扣）' },
  { value: 'free_class', label: '体验课（送 N 节）' },
]

async function load() {
  templates.value = await api.get('/admin/coupon-templates')
  issued.value = await api.get('/admin/coupons')
  if (!members.value.length) {
    const m = await api.get('/admin/members', { params: { role: 'member', size: 500 } })
    members.value = m.items
  }
}

function openCreate() {
  form.value = { name: '', type: 'discount', value: 1000, min_amount: 0, valid_days: 30, applicable_category_id: null, description: '', is_active: true }
  showCreate.value = true
}

async function save() {
  try {
    await api.post('/admin/coupon-templates', form.value)
    ElMessage.success('已创建')
    showCreate.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function openGrant(t) {
  grantForm.value = { template_id: t.id, member_ids: [], _name: t.name }
  showGrant.value = true
}

async function grant() {
  if (!grantForm.value.member_ids.length) return ElMessage.warning('选择至少一个会员')
  try {
    const r = await api.post('/admin/coupons/grant', { template_id: grantForm.value.template_id, member_ids: grantForm.value.member_ids })
    ElMessage.success(`已发放给 ${r.granted} 位会员`)
    showGrant.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

const memberName = (id) => members.value.find(m => m.id === id)?.name || `#${id}`
const tmplName = (id) => templates.value.find(t => t.id === id)?.name || ''

function valueText(t) {
  if (t.type === 'discount') return `减 ¥${(t.value/100).toFixed(0)}`
  if (t.type === 'percent') return `${t.value}折`
  if (t.type === 'cash') return `¥${(t.value/100).toFixed(0)}`
  if (t.type === 'free_class') return `${t.value} 节`
  return t.value
}

const STATUS_TXT = { unused: '未用', used: '已用', expired: '过期' }

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <h2>优惠券</h2>
      <div class="sub">店长可创建券模板，并发放给会员</div>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="券模板" name="templates">
        <div style="margin-bottom: 16px">
          <el-button type="primary" @click="openCreate">+ 新建模板</el-button>
        </div>
        <el-table :data="templates" empty-text="还没有券模板">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="名称" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ TYPES.find(t => t.value === row.type)?.label.split('（')[0] || row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="面值" width="100">
            <template #default="{ row }">{{ valueText(row) }}</template>
          </el-table-column>
          <el-table-column label="门槛" width="100">
            <template #default="{ row }">{{ row.min_amount ? `满 ¥${(row.min_amount/100).toFixed(0)}` : '无' }}</template>
          </el-table-column>
          <el-table-column prop="valid_days" label="有效期(天)" width="100" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.is_active" type="success" size="small">在用</el-tag>
              <el-tag v-else type="info" size="small">停用</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openGrant(row)">发放</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="发放记录" name="issued">
        <el-table :data="issued" empty-text="还没有发放过券">
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ dayjs(row.granted_at).format('MM-DD HH:mm') }}</template>
          </el-table-column>
          <el-table-column label="会员" width="120">
            <template #default="{ row }">{{ memberName(row.member_id) }}</template>
          </el-table-column>
          <el-table-column prop="name" label="券名" />
          <el-table-column label="面值" width="120">
            <template #default="{ row }">{{ valueText(row) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'unused' ? 'success' : (row.status === 'used' ? 'info' : 'danger')">
                {{ STATUS_TXT[row.status] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="到期" width="120">
            <template #default="{ row }">
              <span v-if="row.valid_until">{{ dayjs(row.valid_until).format('YYYY-MM-DD') }}</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showCreate" title="新建券模板" width="500px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.name" placeholder="例如：新人体验券" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option v-for="t in TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="面值">
          <el-input-number v-model="form.value" :step="100" :min="0" />
          <span style="color: #888; font-size: 11px; margin-left: 8px">
            {{ form.type === 'discount' || form.type === 'cash' ? '单位：分' : (form.type === 'percent' ? '0-100' : '次数') }}
          </span>
        </el-form-item>
        <el-form-item label="使用门槛(分)" v-if="['discount','cash'].includes(form.type)">
          <el-input-number v-model="form.min_amount" :step="100" :min="0" />
        </el-form-item>
        <el-form-item label="有效期(天)"><el-input-number v-model="form.valid_days" :min="1" :max="3650" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showGrant" :title="`发放: ${grantForm._name}`" width="600px">
      <el-form label-width="100px">
        <el-form-item label="发给会员">
          <el-select v-model="grantForm.member_ids" multiple filterable style="width: 100%" placeholder="搜索手机号或姓名">
            <el-option v-for="m in members" :key="m.id" :label="`${m.name}（${m.phone}）`" :value="m.id" />
          </el-select>
          <div style="font-size: 11px; color: #888; margin-top: 4px">支持多选，会一次发给所有勾选的会员</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGrant = false">取消</el-button>
        <el-button type="primary" @click="grant">确认发放</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }
</style>

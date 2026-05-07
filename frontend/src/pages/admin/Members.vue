<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'
import dayjs from 'dayjs'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const q = ref('')
const tagFilter = ref('')

const showCreate = ref(false)
const form = ref({
  phone: '', name: '', password: '', gender: '', note: '',
  emergency_contact_name: '', emergency_contact_phone: '', health_note: '',
  tags: [],
})

const PRESET_TAGS = ['新人', 'VIP', '老客户', '试听', '月卡', '私教', '流失风险', '生日月']
const TAG_COLOR = {
  '新人':       { bg: '#FAEEDE', color: '#A4836B' },
  'VIP':        { bg: '#F2DDD3', color: '#A4654E' },
  '老客户':     { bg: '#E0E8DC', color: '#6E7E63' },
  '试听':       { bg: '#E8E9E5', color: '#6B6660' },
  '月卡':       { bg: '#DDE5DC', color: '#6E7B73' },
  '私教':       { bg: '#E2D8E4', color: '#7E6A85' },
  '流失风险':   { bg: '#F7E5DD', color: '#8C5640' },
  '生日月':     { bg: '#EDE0E1', color: '#9C7676' },
}
const tagStyle = (t) => TAG_COLOR[t] || { bg: 'var(--ys-bg-soft)', color: 'var(--ys-text-soft)' }
const splitTags = (s) => (s ? String(s).split(/[,，、]\s*/).filter(Boolean) : [])

async function load() {
  const params = { page: page.value, size: size.value }
  if (q.value) params.q = q.value
  if (tagFilter.value) params.tag = tagFilter.value
  const data = await api.get('/admin/members', { params })
  items.value = data.items
  total.value = data.total
}

async function create() {
  try {
    const body = { ...form.value }
    body.tags = (form.value.tags || []).join(',') || null
    if (!body.password) delete body.password
    Object.keys(body).forEach(k => { if (body[k] === '' || body[k] === null) delete body[k] })
    await api.post('/admin/members', body)
    ElMessage.success('已创建')
    showCreate.value = false
    form.value = {
      phone: '', name: '', password: '', gender: '', note: '',
      emergency_contact_name: '', emergency_contact_phone: '', health_note: '',
      tags: [],
    }
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function deactivate(row) {
  await ElMessageBox.confirm(`停用 ${row.name}？停用后无法登录`, '确认', { type: 'warning' })
  await api.post(`/admin/members/${row.id}/deactivate`)
  ElMessage.success('已停用'); await load()
}

async function resetPwd(row) {
  const { value } = await ElMessageBox.prompt(`重置 ${row.name} 的密码`, '新密码', { inputType: 'password' })
  await api.post(`/admin/members/${row.id}/reset-password`, { new_password: value })
  ElMessage.success('已重置')
}

async function quickEditTags(row) {
  const current = splitTags(row.tags).join(',')
  const { value } = await ElMessageBox.prompt(
    `给 ${row.name} 设置标签（多个用逗号分隔）`,
    '会员标签',
    { inputValue: current, inputPlaceholder: '例如：VIP,老客户' },
  )
  await api.patch(`/admin/members/${row.id}`, { tags: value || null })
  ElMessage.success('已更新')
  await load()
}

function exportCsv() {
  fetch('/api/admin/export/members.csv', { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
    .then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `members-${new Date().toISOString().slice(0,10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
    })
}

onMounted(load)
</script>

<template>
  <h2>会员管理</h2>
  <p style="color: var(--ys-text-muted); font-size: 13px; margin: 4px 0 16px">
    工作室会员（顾客）。员工 / 教练分别在
    <router-link to="/admin/staff" style="color: var(--ys-primary-deep)">员工</router-link> /
    <router-link to="/admin/coaches" style="color: var(--ys-primary-deep)">教练</router-link>
    页管理。
  </p>
  <el-card>
    <div class="filters">
      <el-input v-model="q" placeholder="搜手机号/姓名" style="width: 200px" @keyup.enter="load" clearable @clear="load" />
      <el-select v-model="tagFilter" placeholder="标签筛选" clearable filterable allow-create style="width: 160px" @change="load" @clear="load">
        <el-option v-for="t in PRESET_TAGS" :key="t" :label="t" :value="t" />
      </el-select>
      <el-button type="primary" @click="load">搜索</el-button>
      <div style="flex: 1"></div>
      <el-button @click="exportCsv">导出 CSV</el-button>
      <el-button type="primary" @click="showCreate = true">+ 新增会员</el-button>
    </div>

    <el-table :data="items" @row-click="(row) => router.push(`/admin/members/${row.id}`)" style="cursor: pointer">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column label="标签" min-width="180">
        <template #default="{ row }">
          <span v-if="splitTags(row.tags).length" class="tag-row">
            <span v-for="t in splitTags(row.tags)" :key="t" class="ms-tag"
                  :style="{ background: tagStyle(t).bg, color: tagStyle(t).color }">{{ t }}</span>
          </span>
          <el-button v-else size="small" link type="primary" @click.stop="quickEditTags(row)">+ 加标签</el-button>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="140">
        <template #default="{ row }">{{ dayjs(row.created_at).format('YYYY-MM-DD') }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success" size="small">在用</el-tag>
          <el-tag v-else type="info" size="small">停用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click.stop="quickEditTags(row)">标签</el-button>
          <el-button size="small" link type="primary" @click.stop="resetPwd(row)">重置密码</el-button>
          <el-button v-if="row.is_active" size="small" link type="danger" @click.stop="deactivate(row)">停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      style="margin-top: 12px; justify-content: flex-end; display: flex"
      :total="total" v-model:current-page="page" v-model:page-size="size"
      @current-change="load" layout="total, prev, pager, next" />
  </el-card>

  <el-dialog v-model="showCreate" title="新增会员" width="500px">
    <el-form label-width="100px">
      <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="form.password" placeholder="留空 = 手机号后6位" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="form.gender" clearable>
          <el-option label="女" value="female" />
          <el-option label="男" value="male" />
        </el-select>
      </el-form-item>
      <el-form-item label="标签">
        <el-select v-model="form.tags" multiple filterable allow-create default-first-option style="width: 100%" placeholder="选择或输入标签">
          <el-option v-for="t in PRESET_TAGS" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item>
      <el-divider>紧急联系人 / 健康备注</el-divider>
      <el-form-item label="紧急联系人"><el-input v-model="form.emergency_contact_name" placeholder="家属姓名（出意外联系）" /></el-form-item>
      <el-form-item label="紧急电话"><el-input v-model="form.emergency_contact_phone" /></el-form-item>
      <el-form-item label="健康备注">
        <el-input v-model="form.health_note" type="textarea" :rows="2" placeholder="已知伤病 / 过敏 / 不能做的动作" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCreate = false">取消</el-button>
      <el-button type="primary" @click="create">创建</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.tag-row { display: inline-flex; flex-wrap: wrap; gap: 4px; }
.ms-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
</style>

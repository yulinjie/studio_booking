<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'
import { useAuth } from '../../stores/auth'
import dayjs from 'dayjs'

const auth = useAuth()
const items = ref([])
const q = ref('')
const filterRole = ref('')
const loading = ref(false)

const showCreate = ref(false)
const form = ref({ phone: '', name: '', role: 'staff', password: '', note: '' })

const showEdit = ref(false)
const editing = ref(null)
const editForm = ref({})

async function load() {
  loading.value = true
  try {
    const params = {}
    if (q.value) params.q = q.value
    if (filterRole.value) params.role = filterRole.value
    items.value = await api.get('/admin/staff', { params })
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

const stats = computed(() => ({
  admins: items.value.filter(u => u.role === 'admin' && u.is_active).length,
  staffs: items.value.filter(u => u.role === 'staff' && u.is_active).length,
  inactive: items.value.filter(u => !u.is_active).length,
}))

const ROLE_LABEL = { admin: '店长', staff: '前台' }
const ROLE_COLOR = {
  admin: { bg: '#FAEEDE', color: '#A4836B' },
  staff: { bg: '#DDE5DC', color: '#6E7B73' },
}

async function create() {
  try {
    const body = { ...form.value }
    Object.keys(body).forEach(k => { if (body[k] === '' || body[k] === null) delete body[k] })
    await api.post('/admin/staff', body)
    ElMessage.success(`已创建${ROLE_LABEL[form.value.role]} ${form.value.name}`)
    showCreate.value = false
    form.value = { phone: '', name: '', role: 'staff', password: '', note: '' }
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function openEdit(u) {
  editing.value = u
  editForm.value = { name: u.name, role: u.role, note: u.note || '' }
  showEdit.value = true
}

async function saveEdit() {
  try {
    await api.patch(`/admin/staff/${editing.value.id}`, editForm.value)
    ElMessage.success('已保存')
    showEdit.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function resetPwd(u) {
  try {
    const { value } = await ElMessageBox.prompt(
      `重置 ${u.name} 的密码（至少 4 位）`,
      '新密码', { inputType: 'password', inputPattern: /.{4,}/, inputErrorMessage: '至少 4 位' },
    )
    await api.post(`/admin/staff/${u.id}/reset-password`, { new_password: value })
    ElMessage.success(`已重置 ${u.name} 的密码`)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '操作失败')
  }
}

async function deactivate(u) {
  await ElMessageBox.confirm(
    `停用 ${u.name}（${ROLE_LABEL[u.role]}）？停用后他/她无法登录。`,
    '确认', { type: 'warning' },
  )
  try {
    await api.post(`/admin/staff/${u.id}/deactivate`)
    ElMessage.success('已停用'); await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function activate(u) {
  await api.post(`/admin/staff/${u.id}/activate`)
  ElMessage.success('已启用'); await load()
}

const isMe = (u) => u.id === auth.user?.id

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>员工管理</h2>
        <div class="sub">店长（admin）+ 前台（staff）。教练在「教练」页，会员在「会员」页。</div>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">店长</div>
        <div class="kpi-value">{{ stats.admins }}</div>
        <div class="kpi-trend">含你自己</div>
      </div>
      <div class="kpi-card kpi-accent">
        <div class="kpi-label">前台</div>
        <div class="kpi-value">{{ stats.staffs }}</div>
        <div class="kpi-trend">在职</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已停用</div>
        <div class="kpi-value">{{ stats.inactive }}</div>
        <div class="kpi-trend">不能登录</div>
      </div>
    </div>

    <el-card>
      <div class="actions">
        <el-input v-model="q" placeholder="搜手机号/姓名" style="width: 200px" clearable @clear="load" @keyup.enter="load" />
        <el-select v-model="filterRole" placeholder="角色" clearable style="width: 120px" @change="load" @clear="load">
          <el-option label="店长" value="admin" />
          <el-option label="前台" value="staff" />
        </el-select>
        <el-button type="primary" @click="load">搜索</el-button>
        <div style="flex: 1"></div>
        <el-button type="primary" @click="showCreate = true">+ 新增员工</el-button>
      </div>

      <el-table :data="items" v-loading="loading" empty-text="还没有员工记录">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column label="姓名" width="140">
          <template #default="{ row }">
            {{ row.name }}
            <span v-if="isMe(row)" class="me-chip">我</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <span class="role-tag" :style="{ background: ROLE_COLOR[row.role]?.bg, color: ROLE_COLOR[row.role]?.color }">
              {{ ROLE_LABEL[row.role] }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" type="success" size="small">在职</el-tag>
            <el-tag v-else type="info" size="small">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入职时间" width="140">
          <template #default="{ row }">{{ dayjs(row.created_at).format('YYYY-MM-DD') }}</template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="120" />
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openEdit(row)" :disabled="isMe(row)">编辑</el-button>
            <el-button size="small" link type="primary" @click="resetPwd(row)" :disabled="isMe(row)">重置密码</el-button>
            <el-button v-if="row.is_active" size="small" link type="danger" @click="deactivate(row)" :disabled="isMe(row)">停用</el-button>
            <el-button v-else size="small" link type="success" @click="activate(row)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-alert type="info" show-icon :closable="false" style="margin-top: 16px">
      <strong>注册方式</strong>：员工不能自助注册。仅店长可以创建员工，新员工的默认密码 = 手机号后 6 位（请告诉他们登录后立即在右上角"修改密码"）。<br>
      <strong>安全护栏</strong>：① 不能改自己的角色或停用自己 ② 至少要保留一位在职店长（防失锁）③ 修改密码 / 角色变更都会进操作日志。
    </el-alert>

    <!-- 创建 -->
    <el-dialog v-model="showCreate" title="新增员工" width="450px">
      <el-form label-width="100px">
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="staff">前台</el-radio>
            <el-radio value="admin">店长</el-radio>
          </el-radio-group>
          <div style="font-size: 11px; color: var(--ys-text-muted); margin-top: 4px">
            前台：日常签到 / 收银 / 录入；店长：全部权限 + 设置 + 工资条 + 审计
          </div>
        </el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="form.password" placeholder="留空 = 手机号后 6 位" />
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑 -->
    <el-dialog v-model="showEdit" title="编辑员工" width="450px">
      <el-form label-width="100px" v-if="editing">
        <el-form-item label="姓名"><el-input v-model="editForm.name" /></el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="editForm.role">
            <el-radio value="staff">前台</el-radio>
            <el-radio value="admin">店长</el-radio>
          </el-radio-group>
          <div v-if="editing.role === 'admin' && editForm.role !== 'admin'"
               style="font-size: 11px; color: var(--ys-warning); margin-top: 4px">
            ⚠ 把店长降为前台后，他将失去工资条 / 设置 / 审计 / 员工管理 的权限
          </div>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="editForm.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 12px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }

.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 16px 0; }
.kpi-card { background: var(--ys-bg-card); border: 1px solid var(--ys-line); border-radius: var(--ys-radius); padding: 16px 18px; position: relative; overflow: hidden; }
.kpi-card::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 2px; background: linear-gradient(90deg, var(--ys-primary), transparent); opacity: 0.5; }
.kpi-accent { background: linear-gradient(135deg, var(--ys-primary-bg) 0%, var(--ys-bg-card) 100%); }
.kpi-label { font-size: 12px; color: var(--ys-text-muted); letter-spacing: 2px; }
.kpi-value { font-size: 28px; font-weight: 300; color: var(--ys-text); margin: 6px 0 2px; font-variant-numeric: tabular-nums; }
.kpi-trend { font-size: 11px; color: var(--ys-text-muted); }

.actions { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; }
.role-tag { font-size: 11px; padding: 3px 10px; border-radius: 10px; letter-spacing: 1px; }
.me-chip { font-size: 10px; padding: 1px 6px; border-radius: 4px; background: var(--ys-accent); color: white; margin-left: 6px; letter-spacing: 1px; }
</style>

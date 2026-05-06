<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const coaches = ref([])
const candidates = ref([])
const showCreate = ref(false)
const showEdit = ref(false)
const editing = ref(null)
const form = ref({})
const editForm = ref({})

const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

async function load() {
  coaches.value = await api.get('/coaches')
  // 候选用户：role 为 coach 但还没建 Coach 资料 / 或所有非 member 用户
  const m = await api.get('/admin/members', { params: { size: 200 } })
  const existingUserIds = new Set(coaches.value.map(c => c.user_id))
  candidates.value = m.items.filter(u => !existingUserIds.has(u.id) && u.role !== 'member')
}

function openCreate() {
  form.value = {
    user_id: candidates.value[0]?.id, title: '', bio: '', specialties: '', is_active: true, avatar: '',
    base_salary: 0, pay_per_session: 0, commission_bps: 0, pay_per_attendee: 0,
  }
  showCreate.value = true
}

function openEdit(coach) {
  editing.value = coach
  editForm.value = {
    title: coach.title || '',
    bio: coach.bio || '',
    specialties: coach.specialties || '',
    base_salary: coach.base_salary || 0,
    pay_per_session: coach.pay_per_session || 0,
    commission_bps: coach.commission_bps || 0,
    pay_per_attendee: coach.pay_per_attendee || 0,
    is_active: coach.is_active,
  }
  showEdit.value = true
}

async function saveEdit() {
  try {
    await api.patch(`/admin/coaches/${editing.value.id}`, editForm.value)
    ElMessage.success('已保存')
    showEdit.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function save() {
  try {
    const body = { ...form.value }
    delete body.avatar  // Coach 模型暂无 avatar 字段，先存 user.avatar
    await api.post('/admin/coaches', body)
    if (form.value.avatar) {
      await api.patch(`/admin/members/${form.value.user_id}`, { avatar: form.value.avatar })
    }
    ElMessage.success('教练已添加')
    showCreate.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function onAvatarSuccess(resp) {
  form.value.avatar = resp.url
  ElMessage.success('头像已上传')
}

const userMap = ref({})
async function loadUserMap() {
  const m = await api.get('/admin/members', { params: { size: 500 } })
  userMap.value = Object.fromEntries(m.items.map(u => [u.id, u]))
}

const userName = (id) => userMap.value[id]?.name || `#${id}`
const userPhone = (id) => userMap.value[id]?.phone || ''
const userAvatar = (id) => userMap.value[id]?.avatar

onMounted(async () => { await loadUserMap(); await load() })
</script>

<template>
  <div>
    <div class="page-head">
      <h2>教练</h2>
      <div class="sub">{{ coaches.length }} 位在职 · 工作室核心资产</div>
    </div>

    <div class="actions">
      <el-button type="primary" @click="openCreate">+ 新增教练</el-button>
    </div>

    <div v-if="!coaches.length" class="empty">
      <div class="empty-icon">⌗</div>
      <div class="empty-text">还没有教练资料</div>
      <div class="empty-sub">先在「会员」里把教练手机号注册进来，再来这里添加教练资料</div>
    </div>

    <div v-else class="grid">
      <div v-for="c in coaches" :key="c.id" class="coach-card" @click="openEdit(c)">
        <div class="avatar-block">
          <img v-if="userAvatar(c.user_id)" :src="userAvatar(c.user_id)" class="avatar-img" />
          <div v-else class="avatar-fallback">{{ userName(c.user_id)[0] }}</div>
          <div class="online-dot" v-if="c.is_active"></div>
        </div>
        <div class="info-block">
          <div class="name">{{ userName(c.user_id) }}</div>
          <div class="title">{{ c.title || '— 教练 —' }}</div>
          <div class="phone">{{ userPhone(c.user_id) }}</div>
          <div v-if="c.specialties" class="tags">
            <span v-for="t in c.specialties.split(/[,，、]\s*/)" :key="t" class="tag">{{ t }}</span>
          </div>
          <div v-if="c.bio" class="bio">{{ c.bio }}</div>
          <div class="salary-line" v-if="c.base_salary || c.pay_per_session || c.commission_bps">
            💰
            <span v-if="c.base_salary">底 ¥{{ (c.base_salary/100).toFixed(0) }}</span>
            <span v-if="c.pay_per_session">· 课时 ¥{{ (c.pay_per_session/100).toFixed(0) }}</span>
            <span v-if="c.commission_bps">· 提 {{ (c.commission_bps/100).toFixed(1) }}%</span>
          </div>
          <div v-else class="salary-empty">💡 点击设置薪酬</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" title="新增教练" width="500px">
      <el-form label-width="100px">
        <el-form-item label="基础用户">
          <el-select v-model="form.user_id" placeholder="从已有用户中选" filterable style="width: 100%">
            <el-option v-for="u in candidates" :key="u.id" :label="`${u.name}（${u.phone}）`" :value="u.id" />
          </el-select>
          <div style="color: #9E9890; font-size: 11px; line-height: 1.4; margin-top: 4px">
            没看到要的人？先在「会员」页用教练的手机号注册一个账号
          </div>
        </el-form-item>
        <el-form-item label="头衔">
          <el-input v-model="form.title" placeholder="例如：高级普拉提教练" />
        </el-form-item>
        <el-form-item label="头像">
          <el-upload action="/api/admin/upload" :headers="uploadHeaders" :show-file-list="false" :on-success="onAvatarSuccess" name="file" accept="image/*">
            <el-button size="small">{{ form.avatar ? '更换头像' : '点击上传' }}</el-button>
          </el-upload>
          <img v-if="form.avatar" :src="form.avatar" style="height: 60px; margin-left: 12px; vertical-align: middle; border-radius: 50%" />
        </el-form-item>
        <el-form-item label="擅长">
          <el-input v-model="form.specialties" placeholder="多个用逗号分隔，如：器械普拉提, 阿斯汤加, 阴瑜伽" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.bio" type="textarea" :rows="3" placeholder="教练自我介绍 / 资历" />
        </el-form-item>

        <el-divider>薪酬配置（可空，后期再设）</el-divider>
        <el-form-item label="月度底薪">
          <el-input-number v-model="form.base_salary" :step="100000" :min="0" />
          <span class="hint">分。¥{{ (form.base_salary/100 || 0).toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="每节课时费">
          <el-input-number v-model="form.pay_per_session" :step="5000" :min="0" />
          <span class="hint">分。¥{{ (form.pay_per_session/100 || 0).toFixed(2) }} / 节</span>
        </el-form-item>
        <el-form-item label="每人头补贴">
          <el-input-number v-model="form.pay_per_attendee" :step="500" :min="0" />
          <span class="hint">分。¥{{ (form.pay_per_attendee/100 || 0).toFixed(2) }} / 人</span>
        </el-form-item>
        <el-form-item label="课程价提成">
          <el-input-number v-model="form.commission_bps" :step="100" :min="0" :max="10000" />
          <span class="hint">基点（100=1%）。当前 {{ (form.commission_bps/100 || 0).toFixed(2) }}%</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" :title="`编辑教练 ${userName(editing?.user_id)}`" width="500px">
      <el-form label-width="100px" v-if="editing">
        <el-form-item label="头衔"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="擅长"><el-input v-model="editForm.specialties" placeholder="多个用逗号分隔" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="editForm.bio" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" active-text="在职" inactive-text="离职" />
        </el-form-item>

        <el-divider>薪酬配置</el-divider>
        <el-alert type="info" show-icon :closable="false" style="margin-bottom: 14px">
          工资 = 底薪 + Σ(课时费 + 签到 × 人头补贴 + 签到 × 课程价 × 提成%)。改完保存后下个月报表生效。
        </el-alert>
        <el-form-item label="月度底薪">
          <el-input-number v-model="editForm.base_salary" :step="100000" :min="0" />
          <span class="hint">分。¥{{ (editForm.base_salary/100 || 0).toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="每节课时费">
          <el-input-number v-model="editForm.pay_per_session" :step="5000" :min="0" />
          <span class="hint">分。¥{{ (editForm.pay_per_session/100 || 0).toFixed(2) }} / 节</span>
        </el-form-item>
        <el-form-item label="每人头补贴">
          <el-input-number v-model="editForm.pay_per_attendee" :step="500" :min="0" />
          <span class="hint">分。¥{{ (editForm.pay_per_attendee/100 || 0).toFixed(2) }} / 人</span>
        </el-form-item>
        <el-form-item label="课程价提成">
          <el-input-number v-model="editForm.commission_bps" :step="100" :min="0" :max="10000" />
          <span class="hint">基点（100=1%）。当前 {{ (editForm.commission_bps/100 || 0).toFixed(2) }}%</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }
.actions { margin-bottom: 16px; }

.empty {
  text-align: center;
  padding: 80px 20px;
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  border: 1px dashed var(--ys-border);
}
.empty-icon { font-size: 48px; color: var(--ys-text-light); }
.empty-text { font-size: 16px; margin-top: 12px; color: var(--ys-text-soft); letter-spacing: 1px; }
.empty-sub { font-size: 12px; color: var(--ys-text-muted); margin-top: 6px; max-width: 320px; margin-left: auto; margin-right: auto; line-height: 1.6; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.coach-card {
  display: grid;
  grid-template-columns: 84px 1fr;
  gap: 16px;
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  border: 1px solid var(--ys-line);
  padding: 18px;
  box-shadow: var(--ys-shadow-sm);
  transition: transform 0.18s, box-shadow 0.18s;
}
.coach-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--ys-shadow);
}
.avatar-block {
  position: relative;
  width: 84px; height: 84px;
}
.avatar-img, .avatar-fallback {
  width: 84px; height: 84px;
  border-radius: 50%;
  object-fit: cover;
}
.avatar-fallback {
  background: linear-gradient(135deg, var(--ys-primary-light), var(--ys-accent));
  color: white;
  text-align: center;
  line-height: 84px;
  font-size: 32px;
  font-weight: 300;
}
.online-dot {
  position: absolute;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: var(--ys-success);
  border: 2px solid var(--ys-bg-card);
  bottom: 4px; right: 4px;
}
.info-block { min-width: 0; }
.name {
  font-size: 17px;
  font-weight: 500;
  color: var(--ys-text);
  letter-spacing: 1px;
}
.title {
  font-size: 12px;
  color: var(--ys-primary-deep);
  letter-spacing: 1px;
  margin: 2px 0 4px;
}
.phone {
  font-size: 12px;
  color: var(--ys-text-muted);
  font-variant-numeric: tabular-nums;
  letter-spacing: 1px;
}
.tags { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px; }
.tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--ys-primary-bg);
  color: var(--ys-primary-deep);
  border-radius: 4px;
}
.bio {
  margin-top: 8px;
  font-size: 12px;
  color: var(--ys-text-soft);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.coach-card { cursor: pointer; }
.salary-line {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--ys-line);
  font-size: 12px;
  color: var(--ys-accent-deep);
  letter-spacing: 0.5px;
}
.salary-line span { margin-right: 4px; }
.salary-empty {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--ys-line);
  font-size: 11px;
  color: var(--ys-text-light);
}
.hint { margin-left: 8px; font-size: 11px; color: var(--ys-text-muted); }
</style>

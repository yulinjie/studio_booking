<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
import { safeSrc } from '../../composables/security.js'

const coaches = ref([])
const candidates = ref([])
const showCreate = ref(false)
const showEdit = ref(false)
const editing = ref(null)
const form = ref({})
const editForm = ref({})

const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

const userMap = ref({})
const userName = (id) => userMap.value[id]?.name || `#${id}`
const userPhone = (id) => userMap.value[id]?.phone || ''
const userAvatar = (id) => userMap.value[id]?.avatar

async function load() {
  coaches.value = await api.get('/coaches')
  // 历史 bug：之前用 /admin/members?size=200 拉 userMap，但该接口只返回 role=member。
  // 教练 (role=coach) 的 user 信息根本拿不到，所以列表显示 #user_id，
  // 编辑面板看不到姓名/手机/头像。改成按 user_id 批量拉 /admin/members/{id}（不限 role）。
  const userIds = [...new Set(coaches.value.map((c) => c.user_id))]
  if (userIds.length) {
    const users = await Promise.all(
      userIds.map((id) => api.get(`/admin/members/${id}`).catch(() => null)),
    )
    userMap.value = Object.fromEntries(users.filter(Boolean).map((u) => [u.id, u]))
  }
}

function openCreate() {
  form.value = {
    phone: '', name: '', password: '',
    title: '', bio: '', specialties: '', is_active: true, avatar: '',
    base_salary: 0, pay_per_session: 0, commission_bps: 0, pay_per_attendee: 0,
  }
  showCreate.value = true
}

function openEdit(coach) {
  editing.value = coach
  editForm.value = {
    // User 字段（avatar 走 /admin/members PATCH，独立提交）
    avatar: userAvatar(coach.user_id) || '',
    // Coach 字段（走 /admin/coaches PATCH）
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
    const userId = editing.value.user_id
    const originalAvatar = userAvatar(userId) || ''
    const newAvatar = editForm.value.avatar || ''

    // 1. 头像有变更 → 单独 PATCH user
    if (newAvatar !== originalAvatar) {
      await api.patch(`/admin/members/${userId}`, { avatar: newAvatar })
    }

    // 2. Coach 表字段
    const { avatar: _ignore, ...coachFields } = editForm.value
    await api.patch(`/admin/coaches/${editing.value.id}`, coachFields)

    ElMessage.success('已保存')
    showEdit.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function save() {
  try {
    const body = { ...form.value }
    if (!body.phone) return ElMessage.warning('手机号必填')
    if (!body.name) return ElMessage.warning('姓名必填')
    delete body.avatar
    if (!body.password) delete body.password
    const created = await api.post('/admin/coaches', body)
    // 上传的头像存在 user.avatar 上
    if (form.value.avatar && created.user_id) {
      await api
        .patch(`/admin/members/${created.user_id}`, { avatar: form.value.avatar })
        .catch((e) => console.warn('[Coaches] 头像保存失败:', e.message))
    }
    ElMessage.success('教练已添加')
    showCreate.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  }
}

function onAvatarSuccess(resp) {
  form.value.avatar = resp.url
  ElMessage.success('头像已上传')
}

function onEditAvatarSuccess(resp) {
  editForm.value.avatar = resp.url
  ElMessage.success('头像已上传，点保存生效')
}

onMounted(load)
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
          <img v-if="safeSrc(userAvatar(c.user_id))" :src="safeSrc(userAvatar(c.user_id))" class="avatar-img" />
          <div v-else class="avatar-fallback">{{ userName(c.user_id)[0] }}</div>
          <div v-if="c.is_active" class="online-dot"></div>
        </div>
        <div class="info-block">
          <div class="name">{{ userName(c.user_id) }}</div>
          <div class="title">{{ c.title || '— 教练 —' }}</div>
          <div class="phone">{{ userPhone(c.user_id) }}</div>
          <div v-if="c.specialties" class="tags">
            <span v-for="t in c.specialties.split(/[,，、]\s*/)" :key="t" class="tag">{{ t }}</span>
          </div>
          <div v-if="c.bio" class="bio">{{ c.bio }}</div>
          <div v-if="c.base_salary || c.pay_per_session || c.commission_bps" class="salary-line">
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
        <el-alert type="info" show-icon :closable="false" style="margin-bottom: 14px">
          系统会自动建一个登录账号给教练。<br>
          初始密码 = 手机号后 6 位（不填密码字段时），他/她登录后请去右上角"修改密码"。<br>
          若该手机号已注册（如本来是会员），系统会自动把账号<b>提升为教练</b>。
        </el-alert>
        <el-form-item label="手机号" required>
          <el-input v-model="form.phone" placeholder="作为登录账号" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" placeholder="教练姓名" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="form.password" placeholder="留空 = 手机号后 6 位" />
        </el-form-item>
        <el-divider>教练资料</el-divider>
        <el-form-item label="头衔">
          <el-input v-model="form.title" placeholder="例如：高级普拉提教练" />
        </el-form-item>
        <el-form-item label="头像">
          <el-upload action="/api/admin/upload" :headers="uploadHeaders" :show-file-list="false" :on-success="onAvatarSuccess" name="file" accept="image/*">
            <el-button size="small">{{ form.avatar ? '更换头像' : '点击上传' }}</el-button>
          </el-upload>
          <img v-if="safeSrc(form.avatar)" :src="safeSrc(form.avatar)" style="height: 60px; margin-left: 12px; vertical-align: middle; border-radius: 50%" />
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
      <el-form v-if="editing" label-width="100px">
        <el-form-item label="基本信息">
          <div style="display: flex; align-items: center; gap: 12px; width: 100%">
            <img
              v-if="safeSrc(editForm.avatar)"
              :src="safeSrc(editForm.avatar)"
              style="width: 56px; height: 56px; border-radius: 50%; object-fit: cover; border: 1px solid var(--ys-line)"
            />
            <div
              v-else
              style="width: 56px; height: 56px; border-radius: 50%; background: var(--ys-bg-soft); display: flex; align-items: center; justify-content: center; color: var(--ys-text-muted); font-size: 22px"
            >
              {{ userName(editing.user_id)[0] }}
            </div>
            <div>
              <div style="font-size: 14px">{{ userName(editing.user_id) }}</div>
              <div style="color: var(--ys-text-muted); font-size: 12px; font-variant-numeric: tabular-nums">
                {{ userPhone(editing.user_id) }}
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="头像">
          <el-upload
            action="/api/admin/upload"
            :headers="uploadHeaders"
            :show-file-list="false"
            :on-success="onEditAvatarSuccess"
            name="file"
            accept="image/*"
          >
            <el-button size="small">{{ editForm.avatar ? '更换头像' : '上传头像' }}</el-button>
          </el-upload>
          <el-button
            v-if="editForm.avatar"
            size="small"
            link
            type="danger"
            style="margin-left: 8px"
            @click="editForm.avatar = ''"
          >
            清除
          </el-button>
        </el-form-item>
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

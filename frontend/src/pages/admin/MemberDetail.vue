<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'
import { useMemberDetail } from '../../composables/useMemberDetail.js'
import MemberEditDialog from '../../components/admin/MemberEditDialog.vue'
import MemberCardDialogs from '../../components/admin/MemberCardDialogs.vue'
import MemberBookSessionDialog from '../../components/admin/MemberBookSessionDialog.vue'

const route = useRoute()
const router = useRouter()
const memberId = Number(route.params.id)

const {
  member,
  cards,
  templates,
  bookings,
  courses,
  coaches,
  categories,
  bookingDisplayList,
  load,
} = useMemberDetail(memberId)

const showEditMember = ref(false)
const showIssue = ref(false)
const showAdjust = ref(false)
const showTopup = ref(false)
const showRefund = ref(false)
const showTx = ref(false)
const showBookSession = ref(false)
const activeCard = ref(null)

function openCardDialog(which, card) {
  activeCard.value = card
  if (which === 'adjust') showAdjust.value = true
  else if (which === 'topup') showTopup.value = true
  else if (which === 'refund') showRefund.value = true
  else if (which === 'tx') showTx.value = true
}

async function freeze(card) {
  await api.post(`/admin/cards/${card.id}/freeze`)
  ElMessage.success('已冻结')
  await load()
}
async function unfreeze(card) {
  await api.post(`/admin/cards/${card.id}/unfreeze`)
  ElMessage.success('已解冻')
  await load()
}

function onMemberSaved(updated) {
  member.value = updated
}

// === 预约相关 actions ===

async function checkInBooking(b) {
  try {
    await api.post('/admin/check-in', { booking_id: b.id })
    ElMessage.success('已签到')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '签到失败')
  }
}

async function cancelBooking(b) {
  try {
    await ElMessageBox.confirm(
      `代会员取消「${b.courseName}」(${dayjs(b.startAt).format('M-D HH:mm')})？\n店长代取消会全额返还卡次。`,
      '确认代取消',
      { type: 'warning', confirmButtonText: '确认取消', cancelButtonText: '我再想想' },
    )
  } catch {
    return
  }
  try {
    await api.post(`/bookings/${b.id}/cancel`)
    ElMessage.success('已取消，卡次已退还')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '取消失败')
  }
}

const STATUS_TEXT = {
  booked: '已预约',
  waitlist: '候补中',
  attended: '已上课',
  cancelled: '已取消',
  late_cancelled: '超时取消',
  no_show: '爽约',
}
const STATUS_TYPE = {
  booked: 'success',
  waitlist: 'warning',
  attended: '',
  cancelled: 'info',
  late_cancelled: 'danger',
  no_show: 'danger',
}

onMounted(load)
</script>

<template>
  <el-button link @click="router.back()">← 返回会员列表</el-button>
  <h2 v-if="member">
    {{ member.name }}
    <span style="color: #888; font-weight: normal; font-size: 14px">
      {{ member.phone }} · {{ member.role }}
    </span>
  </h2>

  <el-card v-if="member" style="margin-bottom: 16px">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>会员资料</b>
        <el-button size="small" @click="showEditMember = true">编辑</el-button>
      </div>
    </template>
    <el-descriptions :column="2" size="small">
      <el-descriptions-item label="性别">{{ member.gender || '-' }}</el-descriptions-item>
      <el-descriptions-item label="备注">{{ member.note || '-' }}</el-descriptions-item>
      <el-descriptions-item label="紧急联系人">
        {{ member.emergency_contact_name || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="紧急电话">
        {{ member.emergency_contact_phone || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="健康备注" :span="2">
        <span :style="{ color: member.health_note ? '#e6a23c' : '#999' }">
          {{ member.health_note || '无' }}
        </span>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>

  <el-card style="margin-bottom: 16px">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>名下卡</b>
        <el-button type="primary" size="small" @click="showIssue = true">+ 开新卡</el-button>
      </div>
    </template>
    <el-table :data="cards" empty-text="还没有任何卡">
      <el-table-column prop="name" label="卡名" />
      <el-table-column prop="type" label="类型" width="100" />
      <el-table-column label="次数/余额" width="140">
        <template #default="{ row }">
          <span v-if="row.type === 'stored'">¥{{ (row.remaining_balance / 100).toFixed(2) }}</span>
          <span v-else-if="row.type === 'period'">不限次</span>
          <span v-else>{{ row.remaining_credits }} 次</span>
        </template>
      </el-table-column>
      <el-table-column label="有效期" width="140">
        <template #default="{ row }">
          <span v-if="row.valid_until">{{ dayjs(row.valid_until).format('YYYY-MM-DD') }}</span>
          <span v-else>永久</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openCardDialog('tx', row)">
            流水
          </el-button>
          <el-button size="small" link type="primary" @click="openCardDialog('adjust', row)">
            调整
          </el-button>
          <el-button
            v-if="row.status === 'active'"
            size="small"
            link
            type="warning"
            @click="freeze(row)"
          >
            冻结
          </el-button>
          <el-button
            v-if="row.status === 'frozen'"
            size="small"
            link
            type="success"
            @click="unfreeze(row)"
          >
            解冻
          </el-button>
          <el-button
            v-if="row.type === 'stored' && ['active', 'used_up'].includes(row.status)"
            size="small"
            link
            type="success"
            @click="openCardDialog('topup', row)"
          >
            充值
          </el-button>
          <el-button
            v-if="['active', 'frozen'].includes(row.status)"
            size="small"
            link
            type="danger"
            @click="openCardDialog('refund', row)"
          >
            退卡
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 她的预约 -->
  <el-card style="margin-bottom: 16px">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>她的预约（{{ bookings.filter(b => ['booked','waitlist'].includes(b.status)).length }} 条进行中 · {{ bookings.length }} 条总计）</b>
        <el-button type="primary" size="small" @click="showBookSession = true">+ 代约课</el-button>
      </div>
    </template>
    <el-table :data="bookingDisplayList" empty-text="该会员还没有预约">
      <el-table-column label="时间" width="180">
        <template #default="{ row }">
          <span v-if="row.startAt">{{ dayjs(row.startAt).format('M-D ddd HH:mm') }}</span>
          <span v-else style="color: #999">未知</span>
        </template>
      </el-table-column>
      <el-table-column label="课程">
        <template #default="{ row }">
          {{ row.courseName }}
          <span v-if="row.room" style="color: #888; font-size: 11px">· {{ row.room }}</span>
        </template>
      </el-table-column>
      <el-table-column label="教练" width="120">
        <template #default="{ row }">{{ row.coachName || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="STATUS_TYPE[row.status]">
            {{ STATUS_TEXT[row.status] || row.status }}
            <span v-if="row.waitlist_order">#{{ row.waitlist_order }}</span>
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'booked'"
            size="small"
            link
            type="primary"
            @click="checkInBooking(row)"
          >
            代签到
          </el-button>
          <el-button
            v-if="['booked', 'waitlist'].includes(row.status)"
            size="small"
            link
            type="danger"
            @click="cancelBooking(row)"
          >
            代取消
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <MemberEditDialog v-model="showEditMember" :member="member" @saved="onMemberSaved" />

  <MemberCardDialogs
    :member-id="memberId"
    :templates="templates"
    :card="activeCard"
    v-model:show-issue="showIssue"
    v-model:show-adjust="showAdjust"
    v-model:show-topup="showTopup"
    v-model:show-refund="showRefund"
    v-model:show-tx="showTx"
    @changed="load"
  />

  <MemberBookSessionDialog
    v-model="showBookSession"
    :member-id="memberId"
    :member-name="member?.name || ''"
    :cards="cards"
    :courses="courses"
    :coaches="coaches"
    :categories="categories"
    :existing-bookings="bookings"
    @booked="load"
  />
</template>

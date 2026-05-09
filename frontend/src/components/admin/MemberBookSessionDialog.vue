<script setup>
/*
  店长/前台代会员约课。流程：
    1. 选日期范围（默认未来 7 天）
    2. 拉该范围内所有 scheduled 课节
    3. 过滤掉会员已经预约（booked/waitlist/attended）的课节
    4. 老板点选某节 → 列出该会员适用此课的 active 卡 → 选卡
    5. POST /bookings { session_id, member_id, card_id } —— 后端识别 admin role 走代约逻辑
*/
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  memberId: { type: Number, required: true },
  memberName: { type: String, default: '' },
  cards: { type: Array, default: () => [] }, // 该会员的全部卡（含非 active）
  courses: { type: Array, default: () => [] },
  coaches: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  existingBookings: { type: Array, default: () => [] }, // 用于过滤已约
})
const emit = defineEmits(['update:modelValue', 'booked'])

const dateRange = ref(7) // 未来 N 天
const allSessions = ref([])
const loading = ref(false)
const submitting = ref(false)
const selectedSession = ref(null)
const selectedCardId = ref(null)

// 已经处于活跃状态（booked/waitlist/attended）的 session_id 集合，避免重复约
const bookedSids = computed(
  () =>
    new Set(
      props.existingBookings
        .filter((b) => ['booked', 'waitlist', 'attended'].includes(b.status))
        .map((b) => b.session_id),
    ),
)

// 可选课节：未来 + 状态 scheduled + 还没被该会员约
const availableSessions = computed(() => {
  const now = dayjs()
  return allSessions.value
    .filter(
      (s) =>
        s.status === 'scheduled' &&
        dayjs(s.start_at).isAfter(now) &&
        !bookedSids.value.has(s.id),
    )
    .sort((a, b) => a.start_at.localeCompare(b.start_at))
})

// 选中课节后，过滤会员可用于此课的 active 卡
const usableCards = computed(() => {
  if (!selectedSession.value) return []
  const course = props.courses.find((c) => c.id === selectedSession.value.course_id)
  const courseCatId = course?.category_id
  return props.cards.filter((c) => {
    if (c.status !== 'active') return false
    if (!c.applicable_category_id) return true // 适用所有类型
    return c.applicable_category_id === courseCatId
  })
})

const courseName = (id) => props.courses.find((c) => c.id === id)?.name || '-'
const coachTitle = (id) => props.coaches.find((c) => c.id === id)?.title || ''
const categoryName = (cid) => {
  const course = props.courses.find((c) => c.id === cid)
  return props.categories.find((cat) => cat.id === course?.category_id)?.name || ''
}

function cardLabel(c) {
  const parts = [c.name]
  if (c.type === 'stored') parts.push(`余额 ¥${(c.remaining_balance / 100).toFixed(2)}`)
  else if (c.type === 'period') parts.push('不限次')
  else parts.push(`剩 ${c.remaining_credits} 次`)
  if (c.valid_until) parts.push(`至 ${dayjs(c.valid_until).format('M-D')}`)
  return parts.join(' · ')
}

async function loadSessions() {
  loading.value = true
  try {
    allSessions.value = await api.get('/sessions', {
      params: {
        start: dayjs().toISOString(),
        end: dayjs().add(dateRange.value, 'day').toISOString(),
      },
    })
  } catch (e) {
    ElMessage.error(e.message || '加载课节失败')
  } finally {
    loading.value = false
  }
}

// dialog 打开时拉数据；切换日期范围时重新拉
watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      selectedSession.value = null
      selectedCardId.value = null
      loadSessions()
    }
  },
)
watch(dateRange, loadSessions)

// 选中课节时清空已选卡（避免上次选的卡不适用本次课）+ 默认选第一张可用卡
watch(selectedSession, () => {
  selectedCardId.value = null
  if (usableCards.value.length === 1) selectedCardId.value = usableCards.value[0].id
})

async function submit() {
  if (!selectedSession.value || !selectedCardId.value) return
  submitting.value = true
  try {
    const r = await api.post('/bookings', {
      session_id: selectedSession.value.id,
      member_id: props.memberId,
      card_id: selectedCardId.value,
    })
    ElMessage.success(r.message || `已为 ${props.memberName || '会员'} 代约`)
    emit('update:modelValue', false)
    emit('booked')
  } catch (e) {
    ElMessage.error(e.message || '代约失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="`为 ${memberName || '会员'} 代约课`"
    width="720px"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <el-form label-width="80px">
      <el-form-item label="日期">
        <el-radio-group v-model="dateRange" size="small">
          <el-radio-button :value="3">未来 3 天</el-radio-button>
          <el-radio-button :value="7">未来 7 天</el-radio-button>
          <el-radio-button :value="14">未来 14 天</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="选课节">
        <el-table
          v-loading="loading"
          :data="availableSessions"
          highlight-current-row
          height="280"
          empty-text="该范围内没有可约课节"
          @current-change="(s) => (selectedSession = s)"
        >
          <el-table-column label="时间" width="160">
            <template #default="{ row }">
              {{ dayjs(row.start_at).format('M-D ddd HH:mm') }}
              <span style="color: #999; font-size: 11px">
                ({{ Math.round((dayjs(row.end_at).diff(dayjs(row.start_at)) / 60000)) }}')
              </span>
            </template>
          </el-table-column>
          <el-table-column label="课程">
            <template #default="{ row }">
              <span>{{ courseName(row.course_id) }}</span>
              <el-tag size="small" style="margin-left: 6px">
                {{ categoryName(row.course_id) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="教练" width="120">
            <template #default="{ row }">{{ coachTitle(row.coach_id) || '-' }}</template>
          </el-table-column>
          <el-table-column label="人数" width="80">
            <template #default="{ row }">
              <span :style="{ color: row.booked_count >= row.capacity ? '#C8927E' : 'inherit' }">
                {{ row.booked_count }}/{{ row.capacity }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-form-item>

      <el-form-item v-if="selectedSession" label="选用卡">
        <el-select
          v-model="selectedCardId"
          :placeholder="usableCards.length ? '选择扣哪张卡' : '该会员没有适用此课的 active 卡'"
          :disabled="!usableCards.length"
          style="width: 100%"
        >
          <el-option
            v-for="c in usableCards"
            :key="c.id"
            :label="cardLabel(c)"
            :value="c.id"
          />
        </el-select>
        <div v-if="!usableCards.length" style="color: #C8927E; font-size: 12px; margin-top: 4px">
          ⚠ 需先在「名下卡」开一张适用于「{{ categoryName(selectedSession.course_id) }}」的卡
        </div>
      </el-form-item>

      <el-alert
        v-if="selectedSession && selectedSession.booked_count >= selectedSession.capacity"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 8px"
      >
        该课节已满员，代约后会进入候补队列
      </el-alert>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="!selectedSession || !selectedCardId"
        @click="submit"
      >
        确认代约
      </el-button>
    </template>
  </el-dialog>
</template>

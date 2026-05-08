<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  courses: { type: Array, default: () => [] },
  coaches: { type: Array, default: () => [] },
  initialDate: { type: Object, default: null }, // dayjs 对象
  initialHour: { type: Number, default: 19 },
})
const emit = defineEmits(['update:modelValue', 'created'])

const form = ref({})

// 每次打开重置表单
watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    const start = (props.initialDate || dayjs())
      .hour(props.initialHour)
      .minute(0)
      .second(0)
      .millisecond(0)
    form.value = {
      course_id: props.courses[0]?.id,
      coach_id: null,
      start_at: start.toISOString().slice(0, 19),
      capacity: null,
      room: '',
    }
  },
)

async function submit() {
  const body = { ...form.value }
  if (!body.coach_id) delete body.coach_id
  if (!body.capacity) delete body.capacity
  try {
    // 先 dry-run 检查冲突
    const check = await api
      .post('/admin/sessions/check-conflict', body)
      .catch(() => ({ ok: true, conflicts: [] }))
    if (!check.ok && check.conflicts.length) {
      const c = check.conflicts[0]
      try {
        await ElMessageBox.confirm(
          `检测到${c.reason}冲突：\n${c.course_name}\n${c.start_at.slice(0, 16).replace('T', ' ')}\n${c.room ? '教室 ' + c.room : ''}\n\n仍要创建吗？`,
          '冲突警告',
          { type: 'warning', confirmButtonText: '强制创建', cancelButtonText: '取消' },
        )
      } catch {
        return
      }
    }
    await api.post('/admin/sessions', body)
    ElMessage.success('已排课')
    emit('update:modelValue', false)
    emit('created')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="单节排课"
    width="500px"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <el-form label-width="100px">
      <el-form-item label="课程">
        <el-select v-model="form.course_id" style="width: 100%">
          <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="教练">
        <el-select v-model="form.coach_id" clearable style="width: 100%">
          <el-option
            v-for="c in coaches"
            :key="c.id"
            :label="c.title || '教练' + c.id"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="开始时间">
        <el-date-picker
          v-model="form.start_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="容量">
        <el-input-number v-model="form.capacity" :min="1" />
      </el-form-item>
      <el-form-item label="教室"><el-input v-model="form.room" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="submit">创建</el-button>
    </template>
  </el-dialog>
</template>

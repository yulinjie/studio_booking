<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  courses: { type: Array, default: () => [] },
  coaches: { type: Array, default: () => [] },
  initialStartDate: { type: String, default: null }, // 'YYYY-MM-DDT00:00:00'
})
const emit = defineEmits(['update:modelValue', 'created'])

const form = ref({})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    form.value = {
      course_id: props.courses[0]?.id,
      coach_id: null,
      weekdays: [0, 2, 4],
      time_of_day: '19:00',
      start_date: props.initialStartDate,
      weeks: 4,
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
    const data = await api.post('/admin/sessions/batch', body)
    ElMessage.success(`已批量创建 ${data.length} 节课`)
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
    title="批量循环排课"
    width="550px"
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
      <el-form-item label="星期">
        <el-checkbox-group v-model="form.weekdays">
          <el-checkbox :value="0">一</el-checkbox><el-checkbox :value="1">二</el-checkbox>
          <el-checkbox :value="2">三</el-checkbox><el-checkbox :value="3">四</el-checkbox>
          <el-checkbox :value="4">五</el-checkbox><el-checkbox :value="5">六</el-checkbox>
          <el-checkbox :value="6">日</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      <el-form-item label="时间">
        <el-input v-model="form.time_of_day" placeholder="HH:MM 例如 19:00" />
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker
          v-model="form.start_date"
          type="date"
          value-format="YYYY-MM-DDT00:00:00"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="连续周数">
        <el-input-number v-model="form.weeks" :min="1" :max="52" />
      </el-form-item>
      <el-form-item label="容量">
        <el-input-number v-model="form.capacity" :min="1" />
      </el-form-item>
      <el-form-item label="教室"><el-input v-model="form.room" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="submit">批量创建</el-button>
    </template>
  </el-dialog>
</template>

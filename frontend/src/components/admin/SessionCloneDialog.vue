<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  weekStart: { type: Object, required: true }, // dayjs
  weekEnd: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'cloned'])

const form = ref({ mode: 'this_to_next', offset_days: 7 })
const submitting = ref(false)

watch(
  () => props.modelValue,
  (v) => {
    if (v) form.value = { mode: 'this_to_next', offset_days: 7 }
  },
)

const targetLabel = computed(() => {
  const m = form.value.mode
  if (m === 'last_to_this') return props.weekStart
  return props.weekStart.add(m === 'custom' ? form.value.offset_days : 7, 'day')
})

async function submit() {
  submitting.value = true
  try {
    let from_start, from_end, offset_days
    if (form.value.mode === 'this_to_next') {
      from_start = props.weekStart.toISOString()
      from_end = props.weekEnd.toISOString()
      offset_days = 7
    } else if (form.value.mode === 'last_to_this') {
      from_start = props.weekStart.subtract(7, 'day').toISOString()
      from_end = props.weekStart.toISOString()
      offset_days = 7
    } else {
      from_start = props.weekStart.toISOString()
      from_end = props.weekEnd.toISOString()
      offset_days = form.value.offset_days
    }
    const r = await api.post('/admin/sessions/clone-range', {
      from_start,
      from_end,
      offset_days,
    })
    ElMessage.success(
      `已克隆 ${r.cloned} 节课${r.skipped ? `（跳过 ${r.skipped} 节已取消）` : ''}`,
    )
    emit('update:modelValue', false)
    emit('cloned', { mode: form.value.mode, ...r })
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="克隆排课"
    width="500px"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <el-alert type="info" show-icon :closable="false" style="margin-bottom: 14px">
      把整周排课（含教练 / 教室 / 容量 / 课程）一键复制到目标周。已有预约/已结/已取消不会被克隆，新课表都是空状态。
    </el-alert>
    <el-form label-width="100px">
      <el-form-item label="克隆方式">
        <el-radio-group v-model="form.mode">
          <el-radio value="this_to_next">本周 → 下周</el-radio>
          <el-radio value="last_to_this">上周 → 本周</el-radio>
          <el-radio value="custom">自定义偏移</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.mode === 'custom'" label="偏移天数">
        <el-input-number v-model="form.offset_days" :step="7" :min="1" :max="365" />
        <span class="hint" style="margin-left: 8px; font-size: 11px; color: #888">
          本周复制到 {{ form.offset_days }} 天后
        </span>
      </el-form-item>
      <el-form-item label="源 / 目标">
        <span style="font-size: 12px; color: var(--ys-text-muted)">
          {{ weekStart.format('M月D日') }} - {{ weekEnd.subtract(1, 'day').format('M月D日') }}
          →
          {{ targetLabel.format('M月D日') }} 起
        </span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确认克隆</el-button>
    </template>
  </el-dialog>
</template>

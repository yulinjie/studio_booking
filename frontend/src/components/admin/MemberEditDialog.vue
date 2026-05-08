<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  member: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const form = ref({})

watch(
  () => props.modelValue,
  (v) => {
    if (!v || !props.member) return
    form.value = {
      name: props.member.name,
      gender: props.member.gender,
      note: props.member.note,
      emergency_contact_name: props.member.emergency_contact_name,
      emergency_contact_phone: props.member.emergency_contact_phone,
      health_note: props.member.health_note,
    }
  },
)

async function save() {
  try {
    const updated = await api.patch(`/admin/members/${props.member.id}`, form.value)
    emit('saved', updated)
    emit('update:modelValue', false)
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="编辑会员资料"
    width="500px"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <el-form label-width="100px">
      <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="form.gender" clearable>
          <el-option label="女" value="female" />
          <el-option label="男" value="male" />
        </el-select>
      </el-form-item>
      <el-form-item label="店长备注">
        <el-input v-model="form.note" type="textarea" :rows="2" />
      </el-form-item>
      <el-divider>紧急联系</el-divider>
      <el-form-item label="紧急联系人">
        <el-input v-model="form.emergency_contact_name" />
      </el-form-item>
      <el-form-item label="紧急电话">
        <el-input v-model="form.emergency_contact_phone" />
      </el-form-item>
      <el-form-item label="健康备注">
        <el-input
          v-model="form.health_note"
          type="textarea"
          :rows="3"
          placeholder="已知伤病 / 过敏 / 不能做的动作"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

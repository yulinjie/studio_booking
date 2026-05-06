<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'

const items = ref([])
const cats = ref([])
const showForm = ref(false)
const editing = ref(null)
const form = ref({})

async function load() {
  items.value = await api.get('/admin/card-templates')
  cats.value = await api.get('/admin/course-categories')
}

function openCreate() {
  editing.value = null
  form.value = {
    name: '', type: 'times', price: 0,
    initial_credits: 0, initial_balance: 0,
    valid_days: 0, daily_limit: 0,
    applicable_category_id: null, description: '', is_active: true,
  }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row
  form.value = { ...row }
  showForm.value = true
}

async function submit() {
  try {
    if (editing.value) {
      await api.patch(`/admin/card-templates/${editing.value.id}`, form.value)
    } else {
      await api.post('/admin/card-templates', form.value)
    }
    ElMessage.success('已保存')
    showForm.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function remove(row) {
  await ElMessageBox.confirm(`下架"${row.name}"？已发出的卡不受影响`, '确认', { type: 'warning' })
  await api.delete(`/admin/card-templates/${row.id}`)
  ElMessage.success('已下架'); await load()
}

function exportOrders() {
  fetch('/api/admin/export/orders.csv', { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
    .then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `orders-${new Date().toISOString().slice(0,10)}.csv`; a.click()
      URL.revokeObjectURL(url)
    })
}

onMounted(load)
</script>

<template>
  <h2>卡种管理</h2>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>卡种列表（店长在此配置可售卡种）</b>
        <span>
          <el-button size="small" @click="exportOrders">导出订单 CSV</el-button>
          <el-button type="primary" size="small" @click="openCreate">+ 新增卡种</el-button>
        </span>
      </div>
    </template>
    <el-table :data="items">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="卡名" />
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">
            {{ {times:'次卡', period:'期限卡', stored:'储值卡', package:'课包'}[row.type] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="售价" width="100">
        <template #default="{ row }">¥{{ (row.price/100).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="initial_credits" label="初始次数" width="100" />
      <el-table-column label="初始余额" width="100">
        <template #default="{ row }">{{ row.initial_balance ? '¥'+(row.initial_balance/100).toFixed(2) : '-' }}</template>
      </el-table-column>
      <el-table-column label="有效期" width="80">
        <template #default="{ row }">{{ row.valid_days ? row.valid_days+'天' : '永久' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success" size="small">在售</el-tag>
          <el-tag v-else type="info" size="small">下架</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.is_active" size="small" link type="danger" @click="remove(row)">下架</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="showForm" :title="editing ? '编辑卡种' : '新增卡种'" width="600px">
    <el-form label-width="120px">
      <el-form-item label="卡名"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="类型">
        <el-select v-model="form.type" :disabled="!!editing">
          <el-option label="次卡 (买 N 次)" value="times" />
          <el-option label="期限卡 (N 天不限次)" value="period" />
          <el-option label="储值卡 (按价扣)" value="stored" />
          <el-option label="课包 (私教/特定课)" value="package" />
        </el-select>
      </el-form-item>
      <el-form-item label="售价 (分)"><el-input-number v-model="form.price" :step="100" :min="0" /></el-form-item>
      <el-form-item v-if="['times','package'].includes(form.type)" label="初始次数">
        <el-input-number v-model="form.initial_credits" :min="0" />
      </el-form-item>
      <el-form-item v-if="form.type === 'stored'" label="初始余额 (分)">
        <el-input-number v-model="form.initial_balance" :step="100" :min="0" />
      </el-form-item>
      <el-form-item label="有效期 (天)">
        <el-input-number v-model="form.valid_days" :min="0" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">0 = 永久</span>
      </el-form-item>
      <el-form-item v-if="form.type === 'period'" label="每日上限">
        <el-input-number v-model="form.daily_limit" :min="0" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">0 = 不限</span>
      </el-form-item>
      <el-form-item label="适用课程类型">
        <el-select v-model="form.applicable_category_id" clearable>
          <el-option v-for="c in cats" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <span style="color: #888; margin-left: 8px; font-size: 12px">不选 = 所有类型可用</span>
      </el-form-item>
      <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showForm = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

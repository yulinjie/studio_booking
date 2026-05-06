<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/client'
import dayjs from 'dayjs'

const logs = ref([])
const action = ref('')
const targetType = ref('')

const ACTION_LABELS = {
  'user.change_password': '改密码',
  'user.deactivate': '停用会员',
  'user.activate': '启用会员',
  'user.reset_password': '重置密码',
  'card.issue': '开卡',
  'card.refund': '退卡',
  'card.adjust': '调整',
  'card.freeze': '冻结',
  'card.unfreeze': '解冻',
  'booking.create': '预约',
  'booking.cancel': '取消',
  'booking.check_in': '签到',
  'session.cancel': '取消整节',
  'session.no_show': '批量爽约',
}

async function load() {
  const params = {}
  if (action.value) params.action = action.value
  if (targetType.value) params.target_type = targetType.value
  logs.value = await api.get('/admin/audit-logs', { params })
}

onMounted(load)
</script>

<template>
  <h2>操作日志</h2>
  <el-card>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select v-model="action" placeholder="操作类型" clearable style="width: 200px" @change="load" @clear="load">
        <el-option v-for="(label, code) in ACTION_LABELS" :key="code" :label="`${label}（${code}）`" :value="code" />
      </el-select>
      <el-select v-model="targetType" placeholder="对象类型" clearable style="width: 140px" @change="load" @clear="load">
        <el-option label="用户" value="user" />
        <el-option label="卡" value="card" />
        <el-option label="预约" value="booking" />
        <el-option label="排课" value="session" />
      </el-select>
      <el-button type="primary" @click="load">刷新</el-button>
    </div>
    <el-table :data="logs" empty-text="无日志">
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ dayjs(row.ts).format('MM-DD HH:mm:ss') }}</template>
      </el-table-column>
      <el-table-column label="操作员" width="120">
        <template #default="{ row }">{{ row.operator_name || `#${row.operator_id || '-'}` }}</template>
      </el-table-column>
      <el-table-column label="动作" width="160">
        <template #default="{ row }">
          <el-tag size="small">{{ ACTION_LABELS[row.action] || row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="对象" width="160">
        <template #default="{ row }">
          <span v-if="row.target_type">{{ row.target_type }}#{{ row.target_id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="详情">
        <template #default="{ row }">
          <code style="font-size: 12px; color: #666">{{ row.detail }}</code>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

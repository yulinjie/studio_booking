<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const items = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try { items.value = await api.get('/admin/backups') } finally { loading.value = false }
}

const fmtBytes = (n) => {
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  return (n / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

const total = computed(() => items.value.reduce((s, x) => s + x.db_size + x.uploads_size, 0))
const oldest = computed(() => items.value.length ? items.value[items.value.length - 1] : null)
const newest = computed(() => items.value[0])

async function download(name) {
  try {
    const r = await fetch(`/api/admin/backups/${name}/db`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `studio-${name}.db`; a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>数据备份</h2>
        <div class="sub">
          每日 03:00 自动备份 · 保留最近 30 份 ·
          <span v-if="newest" style="color: var(--ys-success)">✓ 最新备份 {{ dayjs(newest.timestamp).fromNow ? dayjs(newest.timestamp).format('YYYY-MM-DD HH:mm') : newest.timestamp }}</span>
          <span v-else style="color: var(--ys-warning)">⚠ 还没有备份记录</span>
        </div>
      </div>
      <el-button @click="load" :loading="loading">刷新</el-button>
    </div>

    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">备份份数</div>
        <div class="kpi-value">{{ items.length }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">总占用</div>
        <div class="kpi-value">{{ fmtBytes(total) }}</div>
      </div>
      <div class="kpi-card kpi-accent">
        <div class="kpi-label">最早一份</div>
        <div class="kpi-value-sm">{{ oldest ? dayjs(oldest.timestamp).format('MM-DD HH:mm') : '—' }}</div>
      </div>
    </div>

    <el-card v-loading="loading">
      <template #header><b>备份列表（最新在前）</b></template>
      <el-table :data="items" empty-text="还没有备份记录（首次将在凌晨 03:00 生成）">
        <el-table-column label="时间戳" width="200">
          <template #default="{ row }">
            <b>{{ dayjs(row.timestamp).format('YYYY-MM-DD HH:mm:ss') }}</b>
          </template>
        </el-table-column>
        <el-table-column label="距今" width="140">
          <template #default="{ row }">
            {{ Math.round((Date.now() - new Date(row.timestamp)) / 86400000 * 10) / 10 }} 天前
          </template>
        </el-table-column>
        <el-table-column label="DB" width="120">
          <template #default="{ row }">{{ fmtBytes(row.db_size) }}</template>
        </el-table-column>
        <el-table-column label="uploads" width="140">
          <template #default="{ row }">{{ fmtBytes(row.uploads_size) }}</template>
        </el-table-column>
        <el-table-column prop="name" label="目录名" min-width="180">
          <template #default="{ row }">
            <code>~/backups/{{ row.name }}/</code>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="download(row.name)">下载 DB</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-alert type="info" show-icon :closable="false" style="margin-top: 16px">
      备份位置：Ubuntu 上 <code>~/backups/yyyymmdd_HHMMSS/</code> 目录。<br>
      恢复方法：把某份 <code>studio.db</code> 复制覆盖到 <code>~/studio_booking/backend/studio.db</code>，然后 <code>sudo systemctl restart studio</code>。<br>
      要把备份推到云端（OSS / 网盘）请告诉我。
    </el-alert>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }
.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px; }
.kpi-card { background: var(--ys-bg-card); border: 1px solid var(--ys-line); border-radius: var(--ys-radius); padding: 16px 18px; }
.kpi-accent { background: linear-gradient(135deg, var(--ys-primary-bg) 0%, var(--ys-bg-card) 100%); }
.kpi-label { font-size: 12px; color: var(--ys-text-muted); letter-spacing: 2px; }
.kpi-value { font-size: 28px; font-weight: 300; color: var(--ys-text); margin-top: 6px; font-variant-numeric: tabular-nums; }
.kpi-value-sm { font-size: 16px; color: var(--ys-text); margin-top: 8px; font-variant-numeric: tabular-nums; }
</style>

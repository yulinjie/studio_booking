<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const cfg = ref({})
const loading = ref(false)
const regUrl = ref('')

async function load() {
  cfg.value = await api.get('/studio/config')
  const r = await api.get('/studio/registration-url')
  regUrl.value = r.url
}

async function save() {
  loading.value = true
  try {
    cfg.value = await api.patch('/admin/studio/config', cfg.value)
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

const qrSrc = computed(() => `/api/studio/registration-qr.png?t=${Date.now()}`)

const uploadAction = '/api/admin/upload'
const uploadHeaders = computed(() => ({ Authorization: `Bearer ${localStorage.getItem('token')}` }))

function onLogoSuccess(resp) {
  cfg.value.logo = resp.url
  ElMessage.success('已上传，记得点保存')
}

function copyUrl() {
  navigator.clipboard?.writeText(regUrl.value).then(() => ElMessage.success('已复制'))
}

function downloadQr() {
  const a = document.createElement('a')
  a.href = qrSrc.value
  a.download = 'registration-qr.png'
  a.click()
}

onMounted(load)
</script>

<template>
  <h2>工作室设置</h2>

  <el-row :gutter="16">
    <el-col :span="14">
      <el-card>
        <template #header><b>基础信息</b></template>
        <el-form label-width="100px">
          <el-form-item label="工作室名称"><el-input v-model="cfg.name" /></el-form-item>
          <el-form-item label="Logo">
            <el-upload :action="uploadAction" :headers="uploadHeaders" :show-file-list="false" :on-success="onLogoSuccess" name="file" accept="image/*">
              <el-button size="small">{{ cfg.logo ? '更换 Logo' : '点击上传' }}</el-button>
            </el-upload>
            <img v-if="cfg.logo" :src="cfg.logo" style="max-height: 60px; margin-left: 12px; vertical-align: middle" />
          </el-form-item>
          <el-form-item label="地址"><el-input v-model="cfg.address" /></el-form-item>
          <el-form-item label="联系电话"><el-input v-model="cfg.phone" /></el-form-item>
          <el-form-item label="营业时间">
            <el-input v-model="cfg.open_time" placeholder="07:00" style="width: 110px" /> 至
            <el-input v-model="cfg.close_time" placeholder="22:00" style="width: 110px" />
          </el-form-item>
          <el-form-item label="公告">
            <el-input v-model="cfg.announcement" type="textarea" :rows="2" placeholder="例如：周一停业" />
          </el-form-item>
          <el-form-item label="预约规则">
            <el-input v-model="cfg.booking_rules" type="textarea" :rows="3" placeholder="给会员看的：取消时限、爽约规则" />
          </el-form-item>
        </el-form>
        <el-button type="primary" :loading="loading" @click="save" style="margin-left: 100px">保存</el-button>
      </el-card>
    </el-col>

    <el-col :span="10">
      <el-card>
        <template #header><b>会员注册二维码</b></template>
        <p style="color: #666; font-size: 13px">打印贴在前台 / 朋友圈分享 / 群里发链接，会员扫码 → 自动跳转注册页</p>
        <div style="text-align: center; padding: 12px">
          <img :src="qrSrc" style="width: 220px; border: 1px solid #eee; padding: 8px" />
        </div>
        <el-input v-model="regUrl" readonly>
          <template #append><el-button @click="copyUrl">复制</el-button></template>
        </el-input>
        <el-button @click="downloadQr" type="primary" plain style="width: 100%; margin-top: 12px">下载二维码图片</el-button>
      </el-card>
    </el-col>
  </el-row>
</template>

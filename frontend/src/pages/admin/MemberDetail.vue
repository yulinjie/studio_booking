<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const memberId = Number(route.params.id)

const member = ref(null)
const cards = ref([])
const templates = ref([])
const showIssue = ref(false)
const issueForm = ref({ template_id: null, method: 'wechat_qr', paid_amount: null, note: '' })
const showAdjust = ref(false)
const adjustForm = ref({ card_id: null, credits_delta: 0, balance_delta: 0, note: '' })
const txList = ref([])
const showTx = ref(false)
const showRefund = ref(false)
const refundForm = ref({ card_id: null, refund_amount: 0, note: '' })
const showEditMember = ref(false)
const editForm = ref({})
const showTopup = ref(false)
const topupForm = ref({ card_id: null, paid_amount: 0, bonus_amount: 0, method: 'wechat_qr', note: '' })

async function load() {
  member.value = await api.get(`/admin/members/${memberId}`)
  cards.value = await api.get('/admin/cards', { params: { member_id: memberId } })
  templates.value = await api.get('/admin/card-templates')
}

async function issue() {
  try {
    const body = { member_id: memberId, ...issueForm.value }
    if (body.paid_amount === null || body.paid_amount === '') delete body.paid_amount
    if (!body.note) delete body.note
    await api.post('/admin/cards/issue', body)
    ElMessage.success('开卡成功')
    showIssue.value = false
    issueForm.value = { template_id: null, method: 'wechat_qr', paid_amount: null, note: '' }
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function openAdjust(card) {
  adjustForm.value = { card_id: card.id, credits_delta: 0, balance_delta: 0, note: '' }
  showAdjust.value = true
}

async function adjust() {
  try {
    const { card_id, credits_delta, balance_delta, note } = adjustForm.value
    await api.post(`/admin/cards/${card_id}/adjust`, { credits_delta, balance_delta, note })
    ElMessage.success('已调整')
    showAdjust.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function viewTx(card) {
  txList.value = await api.get(`/admin/cards/${card.id}/transactions`)
  showTx.value = true
}

async function freeze(card) {
  await api.post(`/admin/cards/${card.id}/freeze`)
  ElMessage.success('已冻结'); await load()
}
async function unfreeze(card) {
  await api.post(`/admin/cards/${card.id}/unfreeze`)
  ElMessage.success('已解冻'); await load()
}

function openRefund(card) {
  refundForm.value = { card_id: card.id, refund_amount: 0, note: '' }
  showRefund.value = true
}

function openTopup(card) {
  topupForm.value = { card_id: card.id, paid_amount: 0, bonus_amount: 0, method: 'wechat_qr', note: '' }
  showTopup.value = true
}

async function topup() {
  try {
    const { card_id, paid_amount, bonus_amount, method, note } = topupForm.value
    if (paid_amount <= 0) return ElMessage.warning('实付金额必须大于 0')
    const r = await api.post(`/admin/cards/${card_id}/topup`, { paid_amount, bonus_amount, method, note: note || null })
    ElMessage.success(`充值成功，新余额 ¥${(r.new_balance/100).toFixed(2)}`)
    showTopup.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function refund() {
  try {
    const { card_id, refund_amount, note } = refundForm.value
    const r = await api.post(`/admin/cards/${card_id}/refund`, { refund_amount, note })
    ElMessage.success(`退卡成功，已取消 ${r.cancelled_bookings} 笔未来预约`)
    showRefund.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function openEditMember() {
  editForm.value = {
    name: member.value.name,
    gender: member.value.gender,
    note: member.value.note,
    emergency_contact_name: member.value.emergency_contact_name,
    emergency_contact_phone: member.value.emergency_contact_phone,
    health_note: member.value.health_note,
  }
  showEditMember.value = true
}

async function saveEdit() {
  try {
    member.value = await api.patch(`/admin/members/${memberId}`, editForm.value)
    showEditMember.value = false
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(load)
</script>

<template>
  <el-button @click="router.back()" link>← 返回会员列表</el-button>
  <h2 v-if="member">{{ member.name }} <span style="color: #888; font-weight: normal; font-size: 14px">{{ member.phone }} · {{ member.role }}</span></h2>

  <el-card v-if="member" style="margin-bottom: 16px">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>会员资料</b>
        <el-button size="small" @click="openEditMember">编辑</el-button>
      </div>
    </template>
    <el-descriptions :column="2" size="small">
      <el-descriptions-item label="性别">{{ member.gender || '-' }}</el-descriptions-item>
      <el-descriptions-item label="备注">{{ member.note || '-' }}</el-descriptions-item>
      <el-descriptions-item label="紧急联系人">{{ member.emergency_contact_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="紧急电话">{{ member.emergency_contact_phone || '-' }}</el-descriptions-item>
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
          <span v-if="row.type === 'stored'">¥{{ (row.remaining_balance/100).toFixed(2) }}</span>
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
          <el-button size="small" link type="primary" @click="viewTx(row)">流水</el-button>
          <el-button size="small" link type="primary" @click="openAdjust(row)">调整</el-button>
          <el-button v-if="row.status === 'active'" size="small" link type="warning" @click="freeze(row)">冻结</el-button>
          <el-button v-if="row.status === 'frozen'" size="small" link type="success" @click="unfreeze(row)">解冻</el-button>
          <el-button v-if="row.type === 'stored' && ['active','used_up'].includes(row.status)" size="small" link type="success" @click="openTopup(row)">充值</el-button>
          <el-button v-if="['active','frozen'].includes(row.status)" size="small" link type="danger" @click="openRefund(row)">退卡</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="showRefund" title="退卡退款" width="500px">
    <el-alert type="warning" show-icon :closable="false" style="margin-bottom: 14px">
      退卡后会自动取消该卡所有未来预约，并释放容量。此操作不可逆。
    </el-alert>
    <el-form label-width="120px">
      <el-form-item label="退款金额(元)">
        <el-input-number v-model="refundForm.refund_amount" :step="100" :min="0" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">单位：分（如 ¥800 填 80000）</span>
      </el-form-item>
      <el-form-item label="退款原因">
        <el-input v-model="refundForm.note" type="textarea" :rows="2" placeholder="必填，留痕用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showRefund = false">取消</el-button>
      <el-button type="danger" @click="refund">确认退卡</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showTopup" title="储值卡充值" width="500px">
    <el-alert type="info" :closable="false" show-icon style="margin-bottom: 14px">
      实付 = 会员真实付款；充送 = 充值赠送（如"充 1000 送 200"则实付 1000，充送 200）
    </el-alert>
    <el-form label-width="120px">
      <el-form-item label="实付金额(分)">
        <el-input-number v-model="topupForm.paid_amount" :step="10000" :min="0" />
        <span style="color: #888; font-size: 11px; margin-left: 8px">¥{{ (topupForm.paid_amount/100).toFixed(2) }}</span>
      </el-form-item>
      <el-form-item label="充送(分，可空)">
        <el-input-number v-model="topupForm.bonus_amount" :step="1000" :min="0" />
        <span v-if="topupForm.bonus_amount" style="color: #888; font-size: 11px; margin-left: 8px">送 ¥{{ (topupForm.bonus_amount/100).toFixed(2) }}</span>
      </el-form-item>
      <el-form-item label="支付方式">
        <el-select v-model="topupForm.method">
          <el-option label="微信收款码" value="wechat_qr" />
          <el-option label="支付宝收款码" value="alipay_qr" />
          <el-option label="现金" value="cash" />
          <el-option label="银行转账" value="bank" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="topupForm.note" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showTopup = false">取消</el-button>
      <el-button type="primary" @click="topup">确认充值</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showEditMember" title="编辑会员资料" width="500px">
    <el-form label-width="100px">
      <el-form-item label="姓名"><el-input v-model="editForm.name" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="editForm.gender" clearable>
          <el-option label="女" value="female" /><el-option label="男" value="male" />
        </el-select>
      </el-form-item>
      <el-form-item label="店长备注"><el-input v-model="editForm.note" type="textarea" :rows="2" /></el-form-item>
      <el-divider>紧急联系</el-divider>
      <el-form-item label="紧急联系人"><el-input v-model="editForm.emergency_contact_name" /></el-form-item>
      <el-form-item label="紧急电话"><el-input v-model="editForm.emergency_contact_phone" /></el-form-item>
      <el-form-item label="健康备注">
        <el-input v-model="editForm.health_note" type="textarea" :rows="3" placeholder="已知伤病 / 过敏 / 不能做的动作" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showEditMember = false">取消</el-button>
      <el-button type="primary" @click="saveEdit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showIssue" title="开新卡" width="500px">
    <el-form label-width="100px">
      <el-form-item label="卡种">
        <el-select v-model="issueForm.template_id" placeholder="选择卡种" style="width: 100%">
          <el-option v-for="t in templates" :key="t.id" :label="`${t.name} (¥${(t.price/100).toFixed(2)})`" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="付款方式">
        <el-select v-model="issueForm.method">
          <el-option label="微信收款码" value="wechat_qr" />
          <el-option label="支付宝收款码" value="alipay_qr" />
          <el-option label="现金" value="cash" />
          <el-option label="银行转账" value="bank" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="实收金额(元)">
        <el-input-number v-model="issueForm.paid_amount" :step="100" :min="0" placeholder="留空=按定价" controls-position="right" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">单位：分（如 ¥88 填 8800）</span>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="issueForm.note" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showIssue = false">取消</el-button>
      <el-button type="primary" @click="issue">开卡</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showAdjust" title="调整卡次数/余额" width="450px">
    <el-form label-width="100px">
      <el-form-item label="次数变化">
        <el-input-number v-model="adjustForm.credits_delta" controls-position="right" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">正数加，负数减</span>
      </el-form-item>
      <el-form-item label="余额变化(分)">
        <el-input-number v-model="adjustForm.balance_delta" controls-position="right" />
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="adjustForm.note" placeholder="必填，留痕用" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAdjust = false">取消</el-button>
      <el-button type="primary" @click="adjust">确认</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showTx" title="卡流水" width="700px">
    <el-table :data="txList">
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ dayjs(row.created_at).format('MM-DD HH:mm:ss') }}</template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column label="次数变化" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.credits_delta > 0 ? 'green' : (row.credits_delta < 0 ? 'red' : '#999') }">
            {{ row.credits_delta > 0 ? '+' : '' }}{{ row.credits_delta }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="余额变化" width="120">
        <template #default="{ row }">
          <span v-if="row.balance_delta">¥{{ (row.balance_delta/100).toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" />
    </el-table>
  </el-dialog>
</template>

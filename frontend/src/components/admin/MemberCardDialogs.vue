<script setup>
/*
  会员名下卡的 5 个操作 dialog 集合：开新卡 / 调整 / 充值 / 退卡 / 流水查看。
  父组件通过对应的 v-model:show-* 控制可见性，通过 :card 传当前操作的卡。
  完成后发射 @changed 让父组件刷新。
*/
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const props = defineProps({
  memberId: { type: Number, required: true },
  templates: { type: Array, default: () => [] },
  // 单卡操作的目标
  card: { type: Object, default: null },
  // 5 个独立 v-model
  showIssue: { type: Boolean, default: false },
  showAdjust: { type: Boolean, default: false },
  showTopup: { type: Boolean, default: false },
  showRefund: { type: Boolean, default: false },
  showTx: { type: Boolean, default: false },
})
const emit = defineEmits([
  'update:showIssue',
  'update:showAdjust',
  'update:showTopup',
  'update:showRefund',
  'update:showTx',
  'changed',
])

const issueForm = ref({ template_id: null, method: 'wechat_qr', paid_amount: null, note: '' })
const adjustForm = ref({ credits_delta: 0, balance_delta: 0, note: '' })
const topupForm = ref({ paid_amount: 0, bonus_amount: 0, method: 'wechat_qr', note: '' })
const refundForm = ref({ refund_amount: 0, note: '' })
const txList = ref([])

// 打开时重置表单 / 拉流水
watch(
  () => props.showIssue,
  (v) => {
    if (v) issueForm.value = { template_id: null, method: 'wechat_qr', paid_amount: null, note: '' }
  },
)
watch(
  () => props.showAdjust,
  (v) => {
    if (v) adjustForm.value = { credits_delta: 0, balance_delta: 0, note: '' }
  },
)
watch(
  () => props.showTopup,
  (v) => {
    if (v) topupForm.value = { paid_amount: 0, bonus_amount: 0, method: 'wechat_qr', note: '' }
  },
)
watch(
  () => props.showRefund,
  (v) => {
    if (v) refundForm.value = { refund_amount: 0, note: '' }
  },
)
watch(
  () => props.showTx,
  async (v) => {
    if (v && props.card) {
      txList.value = await api.get(`/admin/cards/${props.card.id}/transactions`)
    }
  },
)

async function issue() {
  try {
    const body = { member_id: props.memberId, ...issueForm.value }
    if (body.paid_amount === null || body.paid_amount === '') delete body.paid_amount
    if (!body.note) delete body.note
    await api.post('/admin/cards/issue', body)
    ElMessage.success('开卡成功')
    emit('update:showIssue', false)
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function adjust() {
  try {
    await api.post(`/admin/cards/${props.card.id}/adjust`, adjustForm.value)
    ElMessage.success('已调整')
    emit('update:showAdjust', false)
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function topup() {
  const { paid_amount, bonus_amount, method, note } = topupForm.value
  if (paid_amount <= 0) return ElMessage.warning('实付金额必须大于 0')
  try {
    const r = await api.post(`/admin/cards/${props.card.id}/topup`, {
      paid_amount,
      bonus_amount,
      method,
      note: note || null,
    })
    ElMessage.success(`充值成功，新余额 ¥${(r.new_balance / 100).toFixed(2)}`)
    emit('update:showTopup', false)
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function refund() {
  try {
    const r = await api.post(`/admin/cards/${props.card.id}/refund`, refundForm.value)
    ElMessage.success(`退卡成功，已取消 ${r.cancelled_bookings} 笔未来预约`)
    emit('update:showRefund', false)
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <!-- 开新卡 -->
  <el-dialog
    :model-value="showIssue"
    title="开新卡"
    width="500px"
    @update:model-value="(v) => emit('update:showIssue', v)"
  >
    <el-form label-width="100px">
      <el-form-item label="卡种">
        <el-select v-model="issueForm.template_id" placeholder="选择卡种" style="width: 100%">
          <el-option
            v-for="t in templates"
            :key="t.id"
            :label="`${t.name} (¥${(t.price / 100).toFixed(2)})`"
            :value="t.id"
          />
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
        <el-input-number
          v-model="issueForm.paid_amount"
          :step="100"
          :min="0"
          placeholder="留空=按定价"
          controls-position="right"
        />
        <span style="color: #888; margin-left: 8px; font-size: 12px">
          单位：分（如 ¥88 填 8800）
        </span>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="issueForm.note" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:showIssue', false)">取消</el-button>
      <el-button type="primary" @click="issue">开卡</el-button>
    </template>
  </el-dialog>

  <!-- 调整卡次数/余额 -->
  <el-dialog
    :model-value="showAdjust"
    title="调整卡次数/余额"
    width="450px"
    @update:model-value="(v) => emit('update:showAdjust', v)"
  >
    <el-form label-width="100px">
      <el-form-item label="次数变化">
        <el-input-number v-model="adjustForm.credits_delta" controls-position="right" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">正数加，负数减</span>
      </el-form-item>
      <el-form-item label="余额变化(分)">
        <el-input-number v-model="adjustForm.balance_delta" controls-position="right" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="adjustForm.note" placeholder="必填，留痕用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:showAdjust', false)">取消</el-button>
      <el-button type="primary" @click="adjust">确认</el-button>
    </template>
  </el-dialog>

  <!-- 储值卡充值 -->
  <el-dialog
    :model-value="showTopup"
    title="储值卡充值"
    width="500px"
    @update:model-value="(v) => emit('update:showTopup', v)"
  >
    <el-alert type="info" :closable="false" show-icon style="margin-bottom: 14px">
      实付 = 会员真实付款；充送 = 充值赠送（如"充 1000 送 200"则实付 1000，充送 200）
    </el-alert>
    <el-form label-width="120px">
      <el-form-item label="实付金额(分)">
        <el-input-number v-model="topupForm.paid_amount" :step="10000" :min="0" />
        <span style="color: #888; font-size: 11px; margin-left: 8px">
          ¥{{ (topupForm.paid_amount / 100).toFixed(2) }}
        </span>
      </el-form-item>
      <el-form-item label="充送(分，可空)">
        <el-input-number v-model="topupForm.bonus_amount" :step="1000" :min="0" />
        <span
          v-if="topupForm.bonus_amount"
          style="color: #888; font-size: 11px; margin-left: 8px"
        >
          送 ¥{{ (topupForm.bonus_amount / 100).toFixed(2) }}
        </span>
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
      <el-button @click="emit('update:showTopup', false)">取消</el-button>
      <el-button type="primary" @click="topup">确认充值</el-button>
    </template>
  </el-dialog>

  <!-- 退卡退款 -->
  <el-dialog
    :model-value="showRefund"
    title="退卡退款"
    width="500px"
    @update:model-value="(v) => emit('update:showRefund', v)"
  >
    <el-alert type="warning" show-icon :closable="false" style="margin-bottom: 14px">
      退卡后会自动取消该卡所有未来预约，并释放容量。此操作不可逆。
    </el-alert>
    <el-form label-width="120px">
      <el-form-item label="退款金额(元)">
        <el-input-number v-model="refundForm.refund_amount" :step="100" :min="0" />
        <span style="color: #888; margin-left: 8px; font-size: 12px">
          单位：分（如 ¥800 填 80000）
        </span>
      </el-form-item>
      <el-form-item label="退款原因">
        <el-input v-model="refundForm.note" type="textarea" :rows="2" placeholder="必填，留痕用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:showRefund', false)">取消</el-button>
      <el-button type="danger" @click="refund">确认退卡</el-button>
    </template>
  </el-dialog>

  <!-- 卡流水 -->
  <el-dialog
    :model-value="showTx"
    title="卡流水"
    width="700px"
    @update:model-value="(v) => emit('update:showTx', v)"
  >
    <el-table :data="txList">
      <el-table-column label="时间" width="160">
        <template #default="{ row }">
          {{ dayjs(row.created_at).format('MM-DD HH:mm:ss') }}
        </template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column label="次数变化" width="100">
        <template #default="{ row }">
          <span
            :style="{
              color:
                row.credits_delta > 0 ? 'green' : row.credits_delta < 0 ? 'red' : '#999',
            }"
          >
            {{ row.credits_delta > 0 ? '+' : '' }}{{ row.credits_delta }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="余额变化" width="120">
        <template #default="{ row }">
          <span v-if="row.balance_delta">¥{{ (row.balance_delta / 100).toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" />
    </el-table>
  </el-dialog>
</template>

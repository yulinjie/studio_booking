/*
  会员详情：基础信息 + 名下卡 + 卡模板。所有写操作完成后调 reload() 刷新。
*/
import { ref } from 'vue'
import api from '../api/client'

export function useMemberDetail(memberId) {
  const member = ref(null)
  const cards = ref([])
  const templates = ref([])

  async function load() {
    const [m, c, t] = await Promise.all([
      api.get(`/admin/members/${memberId}`),
      api.get('/admin/cards', { params: { member_id: memberId } }),
      api.get('/admin/card-templates'),
    ])
    member.value = m
    cards.value = c
    templates.value = t
  }

  return { member, cards, templates, load }
}

<script setup>
// 按需导入实际用到的 lucide 图标，比 import * 节省 ~860KB
// 增加新 icon 时记得在 ICON_MAP 加一行
import { computed } from 'vue'
import {
  AlertCircle, AlertTriangle, Banknote, BookOpen, Bookmark, Cake,
  CalendarDays, CheckCircle2, ChevronLeft, ChevronRight,
  CircleDollarSign, Clock, CreditCard, Database, Download,
  Flower2, Heart, Home, Image, ImagePlus, Inbox, LayoutDashboard,
  LoaderCircle, MapPin, Megaphone, Moon, QrCode, RefreshCw,
  ScrollText, Settings, Shield, Star, TicketPercent, TrendingUp,
  User, UserCheck, UserCog, Users, Wallet, Circle,
} from 'lucide-vue-next'

const ICON_MAP = {
  'alert-circle': AlertCircle,
  'alert-triangle': AlertTriangle,
  'banknote': Banknote,
  'book-open': BookOpen,
  'bookmark': Bookmark,
  'cake': Cake,
  'calendar-days': CalendarDays,
  'check-circle-2': CheckCircle2,
  'chevron-left': ChevronLeft,
  'chevron-right': ChevronRight,
  'circle-dollar-sign': CircleDollarSign,
  'clock': Clock,
  'credit-card': CreditCard,
  'database': Database,
  'download': Download,
  'flower-2': Flower2,
  'heart': Heart,
  'home': Home,
  'image': Image,
  'image-plus': ImagePlus,
  'inbox': Inbox,
  'layout-dashboard': LayoutDashboard,
  'loader-circle': LoaderCircle,
  'map-pin': MapPin,
  'megaphone': Megaphone,
  'moon': Moon,
  'qr-code': QrCode,
  'refresh-cw': RefreshCw,
  'scroll-text': ScrollText,
  'settings': Settings,
  'shield': Shield,
  'star': Star,
  'ticket-percent': TicketPercent,
  'trending-up': TrendingUp,
  'user': User,
  'user-check': UserCheck,
  'user-cog': UserCog,
  'users': Users,
  'wallet': Wallet,
}

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  stroke: { type: [Number, String], default: 1.6 },
  color: { type: String, default: 'currentColor' },
})

const Cmp = computed(() => ICON_MAP[props.name] || Circle)
</script>

<template>
  <component :is="Cmp" :size="size" :stroke-width="stroke" :color="color" />
</template>

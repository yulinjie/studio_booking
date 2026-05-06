<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const cats = ref([])
const courses = ref([])
const tab = ref('courses')

const showCourseForm = ref(false)
const editingCourse = ref(null)
const courseForm = ref({})

const showCatForm = ref(false)
const editingCat = ref(null)
const catForm = ref({})

async function load() {
  cats.value = await api.get('/admin/course-categories')
  courses.value = await api.get('/admin/courses')
}

function openCreateCourse() {
  editingCourse.value = null
  courseForm.value = {
    category_id: cats.value[0]?.id, name: '', description: '',
    duration_minutes: 60, capacity: 12, credit_cost: 1, price: 0, is_active: true,
    cover: '', difficulty: 2, tags: '', suitable_for: '',
  }
  showCourseForm.value = true
}

const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }
function onCoverSuccess(resp) {
  courseForm.value.cover = resp.url
  ElMessage.success('封面已上传')
}

function openEditCourse(row) {
  editingCourse.value = row
  courseForm.value = { ...row }
  showCourseForm.value = true
}

async function saveCourse() {
  try {
    if (editingCourse.value) {
      await api.patch(`/admin/courses/${editingCourse.value.id}`, courseForm.value)
    } else {
      await api.post('/admin/courses', courseForm.value)
    }
    ElMessage.success('已保存')
    showCourseForm.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function openCreateCat() {
  editingCat.value = null
  catForm.value = {
    name: '', code: '', min_capacity: 1, max_capacity: 12,
    requires_coach: true, default_duration_minutes: 60,
    book_window_hours: 720, cancel_deadline_hours: 24,
    no_show_deduct: true, sort_order: 0, is_active: true,
  }
  showCatForm.value = true
}

function openEditCat(row) {
  editingCat.value = row
  catForm.value = { ...row }
  showCatForm.value = true
}

async function saveCat() {
  try {
    if (editingCat.value) {
      await api.patch(`/admin/course-categories/${editingCat.value.id}`, catForm.value)
    } else {
      await api.post('/admin/course-categories', catForm.value)
    }
    ElMessage.success('已保存')
    showCatForm.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

const catName = (id) => cats.value.find(c => c.id === id)?.name || '-'

onMounted(load)
</script>

<template>
  <h2>课程管理</h2>
  <el-tabs v-model="tab">
    <el-tab-pane label="具体课程" name="courses">
      <el-card>
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <b>课程（如"流瑜伽"、"普拉提团课"）</b>
            <el-button type="primary" size="small" @click="openCreateCourse">+ 新增课程</el-button>
          </div>
        </template>
        <el-table :data="courses">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="课名" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">{{ catName(row.category_id) }}</template>
          </el-table-column>
          <el-table-column prop="duration_minutes" label="时长(分)" width="100" />
          <el-table-column prop="capacity" label="容量" width="80" />
          <el-table-column prop="credit_cost" label="扣次" width="80" />
          <el-table-column label="价格" width="100">
            <template #default="{ row }">¥{{ (row.price/100).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.is_active" type="success" size="small">在用</el-tag>
              <el-tag v-else type="info" size="small">停用</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openEditCourse(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-tab-pane>

    <el-tab-pane label="课程类型" name="cats">
      <el-card>
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <b>课程类型（团课/私教/双人/小班 …）</b>
            <el-button type="primary" size="small" @click="openCreateCat">+ 新增类型</el-button>
          </div>
        </template>
        <el-table :data="cats">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="code" label="code" width="100" />
          <el-table-column label="容量" width="100">
            <template #default="{ row }">{{ row.min_capacity }}-{{ row.max_capacity }}</template>
          </el-table-column>
          <el-table-column prop="cancel_deadline_hours" label="取消时限(h)" width="120" />
          <el-table-column label="爽约扣次" width="100">
            <template #default="{ row }">{{ row.no_show_deduct ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openEditCat(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-tab-pane>
  </el-tabs>

  <el-dialog v-model="showCourseForm" :title="editingCourse ? '编辑课程' : '新增课程'" width="500px">
    <el-form label-width="100px">
      <el-form-item label="类型">
        <el-select v-model="courseForm.category_id">
          <el-option v-for="c in cats" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="课名"><el-input v-model="courseForm.name" /></el-form-item>
      <el-form-item label="说明"><el-input v-model="courseForm.description" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="封面图">
        <el-upload action="/api/admin/upload" :headers="uploadHeaders" :show-file-list="false" :on-success="onCoverSuccess" name="file" accept="image/*">
          <el-button size="small">{{ courseForm.cover ? '更换封面' : '点击上传' }}</el-button>
        </el-upload>
        <img v-if="courseForm.cover" :src="courseForm.cover" style="height: 60px; margin-left: 12px; vertical-align: middle; border-radius: 4px" />
      </el-form-item>
      <el-form-item label="时长(分)"><el-input-number v-model="courseForm.duration_minutes" :min="15" /></el-form-item>
      <el-form-item label="容量"><el-input-number v-model="courseForm.capacity" :min="1" /></el-form-item>
      <el-form-item label="扣次"><el-input-number v-model="courseForm.credit_cost" :min="0" /></el-form-item>
      <el-form-item label="单节价(分)"><el-input-number v-model="courseForm.price" :step="100" :min="0" /></el-form-item>
      <el-form-item label="强度">
        <el-rate v-model="courseForm.difficulty" :max="5" :colors="['#C8A48C','#C8A48C','#C8A48C']" />
      </el-form-item>
      <el-form-item label="标签">
        <el-input v-model="courseForm.tags" placeholder="多个用逗号分隔，如：瘦腰,核心,新人友好" />
      </el-form-item>
      <el-form-item label="适合人群">
        <el-input v-model="courseForm.suitable_for" placeholder="如：零基础，办公族，孕产恢复" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCourseForm = false">取消</el-button>
      <el-button type="primary" @click="saveCourse">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showCatForm" :title="editingCat ? '编辑类型' : '新增类型'" width="500px">
    <el-form label-width="120px">
      <el-form-item label="名称"><el-input v-model="catForm.name" /></el-form-item>
      <el-form-item label="code"><el-input v-model="catForm.code" :disabled="!!editingCat" /></el-form-item>
      <el-form-item label="最小容量"><el-input-number v-model="catForm.min_capacity" :min="1" /></el-form-item>
      <el-form-item label="最大容量"><el-input-number v-model="catForm.max_capacity" :min="1" /></el-form-item>
      <el-form-item label="默认时长(分)"><el-input-number v-model="catForm.default_duration_minutes" :min="15" /></el-form-item>
      <el-form-item label="可提前(h)"><el-input-number v-model="catForm.book_window_hours" :min="1" /></el-form-item>
      <el-form-item label="取消时限(h)"><el-input-number v-model="catForm.cancel_deadline_hours" :min="0" /></el-form-item>
      <el-form-item label="爽约扣次">
        <el-switch v-model="catForm.no_show_deduct" />
      </el-form-item>
      <el-form-item label="排序"><el-input-number v-model="catForm.sort_order" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCatForm = false">取消</el-button>
      <el-button type="primary" @click="saveCat">保存</el-button>
    </template>
  </el-dialog>
</template>

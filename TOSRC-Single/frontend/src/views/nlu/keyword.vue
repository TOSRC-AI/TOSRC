<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>关键词管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增关键词
          </el-button>
        </div>
      </template>

      <!-- 筛选区域 -->
      <el-form :model="queryParams" inline class="query-form">
        <el-form-item label="关键词类型">
          <el-select
            v-model="queryParams.type"
            placeholder="请选择类型"
            clearable
            style="width: 180px"
          >
            <el-option label="意图关键词" value="intent" />
            <el-option label="实体关键词" value="entity" />
            <el-option label="情绪关键词" value="emotion" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联ID">
          <el-input-number
            v-model="queryParams.relation_id"
            :min="0"
            placeholder="关联ID"
            style="width: 120px"
            clearable
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.keyword"
            placeholder="请输入关键词"
            style="width: 200px"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 关键词表格 -->
      <el-table
        :data="keywordList"
        row-key="keyword_id"
        border
        v-loading="loading"
      >
        <el-table-column prop="keyword_id" label="ID" width="80" align="center" />
        <el-table-column prop="keyword" label="关键词" min-width="150" />
        <el-table-column prop="type" label="类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)" size="small">
              {{ getTypeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="relation_id" label="关联ID" width="100" align="center" />
        <el-table-column prop="weight" label="权重" width="100" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="row.weight * 100"
              :show-text="false"
              :stroke-width="12"
              style="width: 80px; display: inline-block"
            />
            <span style="margin-left: 5px">{{ row.weight.toFixed(1) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="warning" 
              size="small" 
              @click="handleEdit(row)"
            >
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleQuery"
          @current-change="handleQuery"
        />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="关键词" prop="keyword">
          <el-input v-model="formData.keyword" placeholder="请输入关键词" />
        </el-form-item>
        <el-form-item label="关键词类型" prop="type">
          <el-select v-model="formData.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="意图关键词" value="intent" />
            <el-option label="实体关键词" value="entity" />
            <el-option label="情绪关键词" value="emotion" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联ID" prop="relation_id">
          <el-input-number v-model="formData.relation_id" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="权重" prop="weight">
          <el-input-number v-model="formData.weight" :min="0.1" :max="5" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态" prop="is_enabled">
          <el-switch
            v-model="formData.is_enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, ElForm } from 'element-plus'
import { Plus, Edit, Delete, Search, Refresh } from '@element-plus/icons-vue'
import { 
  getKeywordListApi, 
  addKeywordApi, 
  updateKeywordApi, 
  deleteKeywordApi,
  type Keyword,
  type KeywordForm
} from '@/api/nlu'

const formRef = ref<InstanceType<typeof ElForm>>()
const dialogVisible = ref(false)
const loading = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const keywordList = ref<Keyword[]>([])
const total = ref(0)

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 20,
  type: undefined as string | undefined,
  relation_id: undefined as number | undefined,
  keyword: undefined as string | undefined
})

// 表单数据
const formData = reactive<KeywordForm>({
  keyword: '',
  type: 'intent',
  relation_id: 0,
  weight: 1.0,
  is_enabled: true,
  description: ''
})

// 表单校验规则
const formRules = {
  keyword: [
    { required: true, message: '请输入关键词', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择关键词类型', trigger: 'change' }
  ],
  relation_id: [
    { required: true, message: '请输入关联ID', trigger: 'blur' }
  ],
  weight: [
    { required: true, message: '请输入权重', trigger: 'blur' }
  ]
}

// 弹窗标题
const dialogTitle = computed(() => {
  return isEdit.value ? '编辑关键词' : '新增关键词'
})

// 获取类型标签
const getTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    'intent': '意图关键词',
    'entity': '实体关键词',
    'emotion': '情绪关键词'
  }
  return map[type] || type
}

// 获取类型标签颜色
const getTypeTagType = (type: string) => {
  const map: Record<string, string> = {
    'intent': 'primary',
    'entity': 'success',
    'emotion': 'warning'
  }
  return map[type] || 'info'
}

// 加载关键词列表
const loadKeywordList = async () => {
  loading.value = true
  try {
    const res = await getKeywordListApi(queryParams)
    keywordList.value = res.data.list
    total.value = res.data.total
  } catch (error) {
    ElMessage.error('加载关键词列表失败')
  } finally {
    loading.value = false
  }
}

// 查询
const handleQuery = () => {
  queryParams.page = 1
  loadKeywordList()
}

// 重置查询
const resetQuery = () => {
  Object.assign(queryParams, {
    type: undefined,
    relation_id: undefined,
    keyword: undefined,
    page: 1,
    page_size: 20
  })
  loadKeywordList()
}

// 新增
const handleAdd = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row: Keyword) => {
  isEdit.value = true
  Object.assign(formData, row)
  dialogVisible.value = true
}

// 删除
const handleDelete = (row: Keyword) => {
  ElMessageBox.confirm(
    `确定要删除关键词【${row.keyword}】吗？删除后无法恢复！`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteKeywordApi(row.keyword_id)
      ElMessage.success('删除成功')
      loadKeywordList()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 提交表单
const handleSubmit = () => {
  if (!formRef.value) return
  
  formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (isEdit.value) {
          await updateKeywordApi(formData)
          ElMessage.success('编辑成功')
        } else {
          await addKeywordApi(formData)
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        loadKeywordList()
      } catch (error) {
        ElMessage.error(isEdit.value ? '编辑失败' : '新增失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    keyword_id: undefined,
    keyword: '',
    type: 'intent',
    relation_id: 0,
    weight: 1.0,
    is_enabled: true,
    description: ''
  })
  formRef.value?.resetFields()
}

onMounted(() => {
  loadKeywordList()
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}

.query-form {
  margin-bottom: 20px;
}

.page-container {
  width: 100%;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}
</style>
<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>意图管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增顶级意图
          </el-button>
        </div>
      </template>

      <!-- 树形表格 -->
      <el-table
        :data="intentTree"
        row-key="intent_id"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
      >
        <el-table-column prop="intent_name" label="意图名称" min-width="200" />
        <el-table-column prop="intent_code" label="意图编码" width="150" />
        <el-table-column prop="level" label="层级" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.level }} 级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" align="center" />
        <el-table-column prop="is_enabled" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="{ row }">
            <el-button 
                      type="primary" 
                      size="small" 
                      @click="handleAddChild(row)"
                    >
                      <el-icon><Plus /></el-icon>
                      新增子级
                    </el-button>
                    <el-button 
                      type="warning" 
                      size="small" 
                      @click="handleEdit(row)"
                      :disabled="row.is_builtin === 1"
                    >
                      <el-icon><Edit /></el-icon>
                      编辑
                    </el-button>
                    <el-button 
                      type="danger" 
                      size="small" 
                      @click="handleDelete(row)"
                      :disabled="(row.children && row.children.length > 0) || row.is_builtin === 1"
                    >
                      <el-icon><Delete /></el-icon>
                      删除
                    </el-button>
          </template>
        </el-table-column>
      </el-table>
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
        <el-form-item label="父级意图" prop="parent_id">
          <el-tree-select
            v-model="formData.parent_id"
            :data="intentTreeSelect"
            value-key="intent_id"
            label="intent_name"
            :props="{ children: 'children', label: 'intent_name', value: 'intent_id' }"
            placeholder="选择父级意图，不选则为顶级意图"
            :disabled="isAddChild || isEdit && formData.level === 1"
          />
        </el-form-item>
        <el-form-item label="意图编码" prop="intent_code">
          <el-input v-model="formData.intent_code" placeholder="请输入意图编码（英文标识）" />
        </el-form-item>
        <el-form-item label="意图名称" prop="intent_name">
          <el-input v-model="formData.intent_name" placeholder="请输入意图名称" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="formData.priority" :min="1" :max="100" style="width: 100%" />
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
        <el-button type="primary" @click="handleSubmit" :loading="loading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, ElForm, ElTreeSelect } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { 
  getIntentListApi, 
  addIntentApi, 
  updateIntentApi, 
  deleteIntentApi,
  type Intent,
  type IntentForm
} from '@/api/nlu'

const formRef = ref<InstanceType<typeof ElForm>>()
const dialogVisible = ref(false)
const loading = ref(false)
const intentTree = ref<Intent[]>([])
const isEdit = ref(false)
const isAddChild = ref(false)

// 表单数据
const formData = reactive<IntentForm>({
  intent_code: '',
  intent_name: '',
  parent_id: 0,
  priority: 1,
  is_enabled: true,
  description: ''
})

// 表单校验规则
const formRules = {
  intent_code: [
    { required: true, message: '请输入意图编码', trigger: 'blur' },
    { pattern: /^[a-zA-Z_]+$/, message: '意图编码只能包含英文和下划线', trigger: 'blur' }
  ],
  intent_name: [
    { required: true, message: '请输入意图名称', trigger: 'blur' }
  ],
  priority: [
    { required: true, message: '请输入优先级', trigger: 'blur' }
  ]
}

// 弹窗标题
const dialogTitle = computed(() => {
  if (isEdit.value) return '编辑意图'
  if (isAddChild.value) return '新增子级意图'
  return '新增顶级意图'
})



// 树形选择器数据
const intentTreeSelect = computed(() => {
  return [
    {
      intent_id: 0,
      intent_name: '顶级意图',
      children: intentTree.value
    }
  ]
})

// 加载意图列表
const loadIntentList = async () => {
  try {
    const res = await getIntentListApi()
    intentTree.value = res.data
  } catch (error) {
    ElMessage.error('加载意图列表失败')
  }
}

// 新增顶级意图
const handleAdd = () => {
  isEdit.value = false
  isAddChild.value = false
  resetForm()
  formData.parent_id = 0
  dialogVisible.value = true
}

// 新增子级意图
const handleAddChild = (row: Intent) => {
  isEdit.value = false
  isAddChild.value = true
  resetForm()
  formData.parent_id = row.intent_id
  formData.level = row.level + 1
  dialogVisible.value = true
}

// 编辑意图
const handleEdit = (row: Intent) => {
  isEdit.value = true
  isAddChild.value = false
  Object.assign(formData, row)
  dialogVisible.value = true
}

// 删除意图
const handleDelete = (row: Intent) => {
  ElMessageBox.confirm(
    `确定要删除意图【${row.intent_name}】吗？删除后无法恢复！`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteIntentApi(row.intent_id)
      ElMessage.success('删除成功')
      loadIntentList()
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
      loading.value = true
      try {
        if (isEdit.value) {
          await updateIntentApi(formData)
          ElMessage.success('编辑成功')
        } else {
          await addIntentApi(formData)
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        loadIntentList()
      } catch (error) {
        ElMessage.error(isEdit.value ? '编辑失败' : '新增失败')
      } finally {
        loading.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    intent_id: undefined,
    intent_code: '',
    intent_name: '',
    parent_id: 0,
    level: 1,
    priority: 1,
    is_enabled: true,
    description: ''
  })
  formRef.value?.resetFields()
}

onMounted(() => {
  loadIntentList()
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-container {
  width: 100%;
}
</style>
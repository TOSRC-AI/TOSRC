<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>实体管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增实体
          </el-button>
        </div>
      </template>

      <!-- 筛选区域 -->
      <el-form :model="queryParams" inline class="query-form">
        <el-form-item label="实体类型">
          <el-input
            v-model="queryParams.entity_type"
            placeholder="请输入实体类型"
            style="width: 200px"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="实体名称">
          <el-input
            v-model="queryParams.entity_name"
            placeholder="请输入实体名称"
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

      <!-- 实体表格 -->
      <el-table
        :data="entityList"
        row-key="entity_id"
        border
        v-loading="loading"
      >
        <el-table-column prop="entity_id" label="ID" width="80" align="center" />
        <el-table-column prop="entity_code" label="实体编码" width="150" />
        <el-table-column prop="entity_name" label="实体名称" width="150" />
        <el-table-column prop="entity_type" label="实体类型" width="150">
          <template #default="{ row }">
            <el-tag size="small">{{ row.entity_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
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
        <el-form-item label="实体编码" prop="entity_code">
          <el-input v-model="formData.entity_code" placeholder="请输入实体编码（英文标识）" />
        </el-form-item>
        <el-form-item label="实体名称" prop="entity_name">
          <el-input v-model="formData.entity_name" placeholder="请输入实体名称" />
        </el-form-item>
        <el-form-item label="实体类型" prop="entity_type">
          <el-input v-model="formData.entity_type" placeholder="请输入实体类型" />
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
// 后续补充实体相关API
// import { 
//   getEntityListApi, 
//   addEntityApi, 
//   updateEntityApi, 
//   deleteEntityApi,
//   type Entity,
//   type EntityForm
// } from '@/api/nlu'

interface Entity {
  entity_id: number
  entity_code: string
  entity_name: string
  entity_type: string
  description: string
}

interface EntityForm {
  entity_id?: number
  entity_code: string
  entity_name: string
  entity_type: string
  description: string
}

const formRef = ref<InstanceType<typeof ElForm>>()
const dialogVisible = ref(false)
const loading = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const entityList = ref<Entity[]>([
  {
    entity_id: 1,
    entity_code: 'location',
    entity_name: '位置',
    entity_type: 'location',
    description: '地理位置、城市、区域等'
  },
  {
    entity_id: 2,
    entity_code: 'house_type',
    entity_name: '户型',
    entity_type: 'house',
    description: '房屋户型：一室一厅、两室一厅等'
  },
  {
    entity_id: 3,
    entity_code: 'price',
    entity_name: '金额',
    entity_type: 'number',
    description: '价格、租金、金额等数字信息'
  },
  {
    entity_id: 4,
    entity_code: 'area',
    entity_name: '面积',
    entity_type: 'number',
    description: '面积大小信息'
  },
  {
    entity_id: 5,
    entity_code: 'time',
    entity_name: '时间',
    entity_type: 'time',
    description: '时间、日期等信息'
  },
  {
    entity_id: 6,
    entity_code: 'weather',
    entity_name: '天气',
    entity_type: 'environment',
    description: '天气相关信息'
  }
])
const total = ref(6)

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 20,
  entity_type: undefined as string | undefined,
  entity_name: undefined as string | undefined
})

// 表单数据
const formData = reactive<EntityForm>({
  entity_code: '',
  entity_name: '',
  entity_type: '',
  description: ''
})

// 表单校验规则
const formRules = {
  entity_code: [
    { required: true, message: '请输入实体编码', trigger: 'blur' },
    { pattern: /^[a-zA-Z_]+$/, message: '实体编码只能包含英文和下划线', trigger: 'blur' }
  ],
  entity_name: [
    { required: true, message: '请输入实体名称', trigger: 'blur' }
  ],
  entity_type: [
    { required: true, message: '请输入实体类型', trigger: 'blur' }
  ]
}

// 弹窗标题
const dialogTitle = computed(() => {
  return isEdit.value ? '编辑实体' : '新增实体'
})

// 加载实体列表
const loadEntityList = async () => {
  loading.value = true
  try {
    // 后续替换为真实API调用
    // const res = await getEntityListApi(queryParams)
    // entityList.value = res.data.list
    // total.value = res.data.total
    
    // 临时模拟数据
    let list = [...entityList.value]
    if (queryParams.entity_type) {
      list = list.filter(item => item.entity_type.includes(queryParams.entity_type!))
    }
    if (queryParams.entity_name) {
      list = list.filter(item => item.entity_name.includes(queryParams.entity_name!))
    }
    total.value = list.length
    const start = (queryParams.page - 1) * queryParams.page_size
    const end = start + queryParams.page_size
    entityList.value = list.slice(start, end)
  } catch (error) {
    ElMessage.error('加载实体列表失败')
  } finally {
    loading.value = false
  }
}

// 查询
const handleQuery = () => {
  queryParams.page = 1
  loadEntityList()
}

// 重置查询
const resetQuery = () => {
  Object.assign(queryParams, {
    entity_type: undefined,
    entity_name: undefined,
    page: 1,
    page_size: 20
  })
  loadEntityList()
}

// 新增
const handleAdd = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row: Entity) => {
  isEdit.value = true
  Object.assign(formData, row)
  dialogVisible.value = true
}

// 删除
const handleDelete = (row: Entity) => {
  ElMessageBox.confirm(
    `确定要删除实体【${row.entity_name}】吗？删除后无法恢复！`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 后续替换为真实API调用
      // await deleteEntityApi(row.entity_id)
      const index = entityList.value.findIndex(item => item.entity_id === row.entity_id)
      if (index > -1) {
        entityList.value.splice(index, 1)
        total.value--
      }
      ElMessage.success('删除成功')
      loadEntityList()
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
          // 后续替换为真实API调用
          // await updateEntityApi(formData)
          const index = entityList.value.findIndex(item => item.entity_id === formData.entity_id)
          if (index > -1) {
            Object.assign(entityList.value[index], formData)
          }
          ElMessage.success('编辑成功')
        } else {
          // 后续替换为真实API调用
          // const res = await addEntityApi(formData)
          const newEntity: Entity = {
            ...formData,
            entity_id: Math.max(...entityList.value.map(item => item.entity_id), 0) + 1
          }
          entityList.value.unshift(newEntity)
          total.value++
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        loadEntityList()
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
    entity_id: undefined,
    entity_code: '',
    entity_name: '',
    entity_type: '',
    description: ''
  })
  formRef.value?.resetFields()
}

onMounted(() => {
  loadEntityList()
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
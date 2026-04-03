<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>插件管理</span>
          <el-button type="primary" @click="uploadDialogVisible = true">
            <el-icon><Upload /></el-icon>
            安装插件
          </el-button>
        </div>
      </template>

      <!-- 筛选区域 -->
      <el-form :model="queryParams" inline class="query-form">
        <el-form-item label="插件类型">
          <el-select
            v-model="queryParams.type"
            placeholder="请选择类型"
            clearable
            style="width: 180px"
          >
            <el-option label="行业规则" value="industry" />
            <el-option label="LLM适配器" value="llm_adapter" />
            <el-option label="存储适配器" value="storage_adapter" />
            <el-option label="路由策略" value="route_strategy" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="queryParams.status"
            placeholder="请选择状态"
            clearable
            style="width: 180px"
          >
            <el-option label="已启用" value="enabled" />
            <el-option label="已禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="适配场景">
          <el-input
            v-model="queryParams.scene"
            placeholder="请输入场景编码"
            style="width: 150px"
            clearable
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

      <!-- 插件列表 -->
      <el-table
        :data="pluginList"
        row-key="plugin_id"
        border
        v-loading="loading"
      >
        <el-table-column prop="plugin_id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="插件名称" width="180" />
        <el-table-column prop="type" label="插件类型" width="150" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)" size="small">
              {{ getTypeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="100" align="center" />
        <el-table-column prop="scene" label="适配场景" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" v-if="row.scene">{{ row.scene }}</el-tag>
            <span v-else class="text-gray">通用</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              active-value="enabled"
              inactive-value="disabled"
              @change="togglePluginStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
        <el-table-column prop="update_time" label="更新时间" width="180" align="center" />
        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleConfig(row)"
              :disabled="row.status !== 'enabled'"
            >
              <el-icon><Setting /></el-icon>
              配置
            </el-button>
            <el-button 
              type="info" 
              size="small" 
              @click="handleViewDetail(row)"
            >
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleUninstall(row)"
            >
              <el-icon><Delete /></el-icon>
              卸载
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

    <!-- 插件详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="插件详情"
      width="600px"
      destroy-on-close
    >
      <div v-if="currentPlugin" class="plugin-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="插件名称">
            {{ currentPlugin.name }}
          </el-descriptions-item>
          <el-descriptions-item label="插件类型">
            {{ getTypeLabel(currentPlugin.type) }}
          </el-descriptions-item>
          <el-descriptions-item label="版本">
            {{ currentPlugin.version }}
          </el-descriptions-item>
          <el-descriptions-item label="适配场景">
            {{ currentPlugin.scene || '通用' }}
          </el-descriptions-item>
          <el-descriptions-item label="作者">
            {{ currentPlugin.author }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ currentPlugin.update_time }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ currentPlugin.description }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 安装插件弹窗 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="安装插件"
      width="500px"
      destroy-on-close
    >
      <el-upload
        ref="uploadRef"
        class="upload-area"
        :action="uploadUrl"
        :headers="uploadHeaders"
        :limit="1"
        accept=".zip"
        :file-list="fileList"
        :before-upload="beforeUpload"
        :on-success="onUploadSuccess"
        :on-error="onUploadError"
        :auto-upload="false"
        drag
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将插件包拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">只能上传zip格式的插件包，大小不超过50MB</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploadLoading">安装</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElUpload } from 'element-plus'
import { Search, Refresh, Upload, View, Delete, Setting, UploadFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import dayjs from 'dayjs'

interface Plugin {
  plugin_id: number
  name: string
  type: 'industry' | 'llm_adapter' | 'storage_adapter' | 'route_strategy'
  version: string
  scene: string
  status: 'enabled' | 'disabled'
  description: string
  author: string
  update_time: string
}

const uploadRef = ref<InstanceType<typeof ElUpload>>()
const loading = ref(false)
const uploadLoading = ref(false)
const pluginList = ref<Plugin[]>([
  {
    plugin_id: 1,
    name: '租房行业规则包',
    type: 'industry',
    version: '1.0.0',
    scene: 'rental',
    status: 'enabled',
    description: '租房场景语义识别规则包，包含租房相关意图、实体、情绪识别规则',
    author: 'TOSRC团队',
    update_time: '2026-03-20 12:00:00'
  },
  {
    plugin_id: 2,
    name: 'DeepSeek适配器',
    type: 'llm_adapter',
    version: '1.1.0',
    scene: '',
    status: 'enabled',
    description: 'DeepSeek大模型适配插件，支持DeepSeek全系列模型调用',
    author: 'TOSRC团队',
    update_time: '2026-03-22 10:30:00'
  },
  {
    plugin_id: 3,
    name: '火山引擎适配器',
    type: 'llm_adapter',
    version: '1.0.0',
    scene: '',
    status: 'disabled',
    description: '火山引擎豆包大模型适配插件',
    author: 'TOSRC团队',
    update_time: '2026-03-21 15:00:00'
  },
  {
    plugin_id: 4,
    name: '最高优先级路由策略',
    type: 'route_strategy',
    version: '1.0.0',
    scene: '',
    status: 'enabled',
    description: '优先匹配最高优先级的意图规则，适用于对准确性要求高的场景',
    author: 'TOSRC团队',
    update_time: '2026-03-18 09:00:00'
  }
])
const total = ref(4)
const detailDialogVisible = ref(false)
const uploadDialogVisible = ref(false)
const currentPlugin = ref<Plugin | null>(null)
const fileList = ref([])
const userStore = useUserStore()

// 上传配置
const uploadUrl = '/api/v1/admin/plugin/upload'
const uploadHeaders = {
  'X-Admin-Api-Key': userStore.token
}

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 20,
  type: undefined as string | undefined,
  status: undefined as string | undefined,
  scene: undefined as string | undefined
})

// 获取类型标签
const getTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    'industry': '行业规则',
    'llm_adapter': 'LLM适配器',
    'storage_adapter': '存储适配器',
    'route_strategy': '路由策略'
  }
  return map[type] || type
}

// 获取类型标签颜色
const getTypeTagType = (type: string) => {
  const map: Record<string, string> = {
    'industry': 'primary',
    'llm_adapter': 'success',
    'storage_adapter': 'warning',
    'route_strategy': 'info'
  }
  return map[type] || 'info'
}

// 加载插件列表
const loadPluginList = async () => {
  loading.value = true
  try {
    // 临时模拟数据过滤
    let list = [...pluginList.value]
    if (queryParams.type) {
      list = list.filter(item => item.type === queryParams.type)
    }
    if (queryParams.status) {
      list = list.filter(item => item.status === queryParams.status)
    }
    if (queryParams.scene) {
      list = list.filter(item => item.scene.includes(queryParams.scene!))
    }
    total.value = list.length
    const start = (queryParams.page - 1) * queryParams.page_size
    const end = start + queryParams.page_size
    pluginList.value = list.slice(start, end)
  } catch (error) {
    ElMessage.error('加载插件列表失败')
  } finally {
    loading.value = false
  }
}

// 查询
const handleQuery = () => {
  queryParams.page = 1
  loadPluginList()
}

// 重置查询
const resetQuery = () => {
  Object.assign(queryParams, {
    type: undefined,
    status: undefined,
    scene: undefined,
    page: 1,
    page_size: 20
  })
  loadPluginList()
}

// 切换插件状态
const togglePluginStatus = (row: Plugin) => {
  const action = row.status === 'enabled' ? '启用' : '禁用'
  ElMessageBox.confirm(
    `确定要${action}插件【${row.name}】吗？${action === '启用' ? '启用后插件将立即生效' : '禁用后相关功能将不可用'}！`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 模拟API调用
      ElMessage.success(`插件${action}成功`)
    } catch (error) {
      row.status = row.status === 'enabled' ? 'disabled' : 'enabled'
      ElMessage.error(`插件${action}失败`)
    }
  }).catch(() => {
    row.status = row.status === 'enabled' ? 'disabled' : 'enabled'
  })
}

// 插件配置
const handleConfig = (row: Plugin) => {
  ElMessage.info(`【${row.name}】的配置功能开发中`)
}

// 查看详情
const handleViewDetail = (row: Plugin) => {
  currentPlugin.value = { ...row }
  detailDialogVisible.value = true
}

// 卸载插件
const handleUninstall = (row: Plugin) => {
  ElMessageBox.confirm(
    `确定要卸载插件【${row.name}】吗？卸载后会删除插件所有相关数据，无法恢复！`,
    '警告',
    {
      confirmButtonText: '确定卸载',
      cancelButtonText: '取消',
      type: 'danger'
    }
  ).then(async () => {
    try {
      // 模拟API调用
      const index = pluginList.value.findIndex(item => item.plugin_id === row.plugin_id)
      if (index > -1) {
        pluginList.value.splice(index, 1)
        total.value--
      }
      ElMessage.success('插件卸载成功')
      loadPluginList()
    } catch (error) {
      ElMessage.error('卸载失败')
    }
  })
}

// 上传前校验
const beforeUpload = (file: File) => {
  const isZip = file.type === 'application/zip' || file.name.endsWith('.zip')
  if (!isZip) {
    ElMessage.error('只能上传zip格式的插件包！')
    return false
  }
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('插件包大小不能超过 50MB!')
    return false
  }
  return true
}

// 手动上传
const handleUpload = () => {
  if (uploadRef.value) {
    uploadRef.value.submit()
  }
}

// 上传成功
const onUploadSuccess = () => {
  ElMessage.success('插件安装成功')
  uploadDialogVisible.value = false
  fileList.value = []
  loadPluginList()
}

// 上传失败
const onUploadError = () => {
  ElMessage.error('插件安装失败，请检查插件包格式是否正确')
}

onMounted(() => {
  loadPluginList()
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

.upload-area {
  padding: 20px;
}

.plugin-detail {
  max-height: 500px;
  overflow-y: auto;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}

.text-gray {
  color: #909399;
}
</style>
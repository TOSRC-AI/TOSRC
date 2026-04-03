<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>规则包管理</span>
          <el-button type="primary" @click="uploadDialogVisible = true">
            <el-icon><Upload /></el-icon>
            上传规则包
          </el-button>
        </div>
      </template>

      <!-- 规则包列表 -->
      <el-table
        :data="rulePackageList"
        row-key="scene"
        border
        v-loading="loading"
      >
        <el-table-column prop="scene" label="场景编码" width="150" />
        <el-table-column prop="scene_name" label="场景名称" min-width="180" />
        <el-table-column prop="entity_rule_count" label="实体规则数" width="120" align="center" />
        <el-table-column prop="intent_rule_count" label="意图规则数" width="120" align="center" />
        <el-table-column prop="emotion_rule_count" label="情绪规则数" width="120" align="center" />
        <el-table-column prop="negative_rule_count" label="否定规则数" width="120" align="center" />
        <el-table-column prop="last_modify_time" label="最后修改时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatTime(row.last_modify_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleViewDetail(row)"
            >
              <el-icon><View /></el-icon>
              查看详情
            </el-button>
            <el-button 
              type="warning" 
              size="small" 
              @click="handleReload(row)"
            >
              <el-icon><Refresh /></el-icon>
              重载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 查看详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="规则包详情"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentRulePackage" class="rule-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="场景编码">
            {{ currentRulePackage.scene }}
          </el-descriptions-item>
          <el-descriptions-item label="场景名称">
            {{ currentRulePackage.scene_name }}
          </el-descriptions-item>
          <el-descriptions-item label="实体规则数">
            {{ currentRulePackage.entity_rule_count }}
          </el-descriptions-item>
          <el-descriptions-item label="意图规则数">
            {{ currentRulePackage.intent_rule_count }}
          </el-descriptions-item>
          <el-descriptions-item label="情绪规则数">
            {{ currentRulePackage.emotion_rule_count }}
          </el-descriptions-item>
          <el-descriptions-item label="否定规则数">
            {{ currentRulePackage.negative_rule_count }}
          </el-descriptions-item>
          <el-descriptions-item label="文件路径" :span="2">
            {{ currentRulePackage.file_path }}
          </el-descriptions-item>
        </el-descriptions>

        <el-tabs v-model="activeTab" class="mt-20">
          <el-tab-pane label="实体规则" name="entity">
            <el-table :data="currentRulePackage.entity_rules || []" border size="small">
              <el-table-column prop="name" label="实体名称" width="150" />
              <el-table-column prop="pattern" label="匹配规则" min-width="300" show-overflow-tooltip />
              <el-table-column prop="weight" label="权重" width="100" align="center" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="意图规则" name="intent">
            <el-table :data="currentRulePackage.intent_rules || []" border size="small">
              <el-table-column prop="intent" label="意图名称" width="150" />
              <el-table-column prop="keywords" label="关键词列表" min-width="300" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tag v-for="kw in row.keywords" :key="kw" size="small" style="margin: 2px">
                    {{ kw }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="threshold" label="阈值" width="100" align="center" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 上传规则包弹窗 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传规则包"
      width="500px"
      destroy-on-close
    >
      <el-upload
        ref="uploadRef"
        class="upload-area"
        :action="uploadUrl"
        :headers="uploadHeaders"
        :limit="1"
        accept=".json"
        :file-list="fileList"
        :before-upload="beforeUpload"
        :on-success="onUploadSuccess"
        :on-error="onUploadError"
        :auto-upload="false"
        drag
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">只能上传JSON格式的规则包文件，文件名需以_rules.json结尾</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploadLoading">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElUpload } from 'element-plus'
import { Upload, View, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { 
  getRulePackageListApi, 
  reloadRulePackageApi, 
  uploadRulePackageApi,
  type RulePackage
} from '@/api/nlu'
import dayjs from 'dayjs'

const uploadRef = ref<InstanceType<typeof ElUpload>>()
const loading = ref(false)
const uploadLoading = ref(false)
const rulePackageList = ref<RulePackage[]>([])
const detailDialogVisible = ref(false)
const uploadDialogVisible = ref(false)
const currentRulePackage = ref<RulePackage | null>(null)
const activeTab = ref('entity')
const fileList = ref([])
const userStore = useUserStore()

// 上传配置
const uploadUrl = '/api/v1/admin/rule/upload'
const uploadHeaders = {
  'X-Admin-Api-Key': userStore.token
}

// 格式化时间
const formatTime = (timestamp: number) => {
  return dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

// 加载规则包列表
const loadRulePackageList = async () => {
  loading.value = true
  try {
    const res = await getRulePackageListApi()
    rulePackageList.value = res.data.list
  } catch (error) {
    ElMessage.error('加载规则包列表失败')
  } finally {
    loading.value = false
  }
}

// 查看详情
const handleViewDetail = async (row: RulePackage) => {
  // 这里可以调用详情接口，暂时先用列表数据
  currentRulePackage.value = { ...row }
  detailDialogVisible.value = true
}

// 重载规则包
const handleReload = (row: RulePackage) => {
  ElMessageBox.confirm(
    `确定要重载规则包【${row.scene_name}】吗？重载会更新所有规则到最新版本！`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await reloadRulePackageApi(row.scene)
      ElMessage.success('重载成功')
      loadRulePackageList()
    } catch (error) {
      ElMessage.error('重载失败')
    }
  })
}

// 上传前校验
const beforeUpload = (file: File) => {
  const isJSON = file.type === 'application/json' || file.name.endsWith('_rules.json')
  if (!isJSON) {
    ElMessage.error('只能上传JSON格式的规则包文件，文件名需以_rules.json结尾！')
    return false
  }
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('规则包大小不能超过 10MB!')
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
  ElMessage.success('规则包上传成功')
  uploadDialogVisible.value = false
  fileList.value = []
  loadRulePackageList()
}

// 上传失败
const onUploadError = () => {
  ElMessage.error('规则包上传失败，请检查文件格式是否正确')
}

onMounted(() => {
  loadRulePackageList()
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

.upload-area {
  padding: 20px;
}

.rule-detail {
  max-height: 600px;
  overflow-y: auto;
}

.mt-20 {
  margin-top: 20px;
}
</style>
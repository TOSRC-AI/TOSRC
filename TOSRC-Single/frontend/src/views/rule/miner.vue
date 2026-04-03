<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>规则挖掘</span>
          <el-button type="primary" @click="handleRunMining">
            <el-icon><VideoPlay /></el-icon>
            执行挖掘
          </el-button>
        </div>
      </template>

      <!-- 筛选区域 -->
      <el-form :model="queryParams" inline class="query-form">
        <el-form-item label="规则类型">
          <el-select
            v-model="queryParams.type"
            placeholder="请选择类型"
            clearable
            style="width: 180px"
          >
            <el-option label="实体规则" value="entity" />
            <el-option label="意图规则" value="intent" />
            <el-option label="情绪规则" value="emotion" />
            <el-option label="否定规则" value="negative" />
          </el-select>
        </el-form-item>
        <el-form-item label="审核状态">
          <el-select
            v-model="queryParams.status"
            placeholder="请选择状态"
            clearable
            style="width: 180px"
          >
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="场景">
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

      <!-- 规则表格 -->
      <el-table
        :data="miningRuleList"
        row-key="rule_id"
        border
        v-loading="loading"
      >
        <el-table-column prop="rule_id" label="ID" width="80" align="center" />
        <el-table-column prop="scene" label="场景" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.scene }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="规则类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)" size="small">
              {{ getTypeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="规则内容" min-width="250" show-overflow-tooltip />
        <el-table-column prop="confidence" label="置信度" width="120" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="row.confidence * 100"
              :show-text="false"
              :stroke-width="12"
              :color="getConfidenceColor(row.confidence)"
              style="width: 80px; display: inline-block"
            />
            <span style="margin-left: 5px">{{ (row.confidence * 100).toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="审核状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="挖掘时间" width="180" align="center" />
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="success" 
              size="small" 
              @click="handleApprove(row)"
              :disabled="row.status !== 'pending'"
            >
              <el-icon><Check /></el-icon>
              通过
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleReject(row)"
              :disabled="row.status !== 'pending'"
            >
              <el-icon><Close /></el-icon>
              驳回
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, ElForm } from 'element-plus'
import { Search, Refresh, VideoPlay, Check, Close } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

interface MiningRule {
  rule_id: number
  scene: string
  type: 'entity' | 'intent' | 'emotion' | 'negative'
  content: string
  confidence: number
  status: 'pending' | 'approved' | 'rejected'
  create_time: string
}

const loading = ref(false)
const miningRuleList = ref<MiningRule[]>([
  {
    rule_id: 1,
    scene: 'rental',
    type: 'entity',
    content: '租金价格匹配规则：匹配"[0-9]+[k|w|千|万]?[元|块]?/月?"',
    confidence: 0.92,
    status: 'pending',
    create_time: dayjs().subtract(1, 'hour').format('YYYY-MM-DD HH:mm:ss')
  },
  {
    rule_id: 2,
    scene: 'rental',
    type: 'intent',
    content: '租房咨询意图：包含"租""租房""找房"等关键词',
    confidence: 0.87,
    status: 'approved',
    create_time: dayjs().subtract(2, 'hour').format('YYYY-MM-DD HH:mm:ss')
  },
  {
    rule_id: 3,
    scene: 'rental',
    type: 'emotion',
    content: '不满情绪规则：包含"太贵""不满意""太差"等关键词',
    confidence: 0.78,
    status: 'rejected',
    create_time: dayjs().subtract(3, 'hour').format('YYYY-MM-DD HH:mm:ss')
  },
  {
    rule_id: 4,
    scene: 'weather',
    type: 'intent',
    content: '天气查询意图：包含"天气""温度""下雨"等关键词',
    confidence: 0.95,
    status: 'pending',
    create_time: dayjs().subtract(4, 'hour').format('YYYY-MM-DD HH:mm:ss')
  },
  {
    rule_id: 5,
    scene: 'general',
    type: 'negative',
    content: '否定规则：包含"不""不是""没有"等否定词',
    confidence: 0.89,
    status: 'approved',
    create_time: dayjs().subtract(5, 'hour').format('YYYY-MM-DD HH:mm:ss')
  }
])
const total = ref(5)

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
    'entity': '实体规则',
    'intent': '意图规则',
    'emotion': '情绪规则',
    'negative': '否定规则'
  }
  return map[type] || type
}

// 获取类型标签颜色
const getTypeTagType = (type: string) => {
  const map: Record<string, string> = {
    'entity': 'primary',
    'intent': 'success',
    'emotion': 'warning',
    'negative': 'info'
  }
  return map[type] || 'info'
}

// 获取状态标签
const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    'pending': '待审核',
    'approved': '已通过',
    'rejected': '已驳回'
  }
  return map[status] || status
}

// 获取状态标签颜色
const getStatusTagType = (status: string) => {
  const map: Record<string, string> = {
    'pending': 'warning',
    'approved': 'success',
    'rejected': 'danger'
  }
  return map[status] || 'info'
}

// 获取置信度颜色
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.9) return '#67c23a'
  if (confidence >= 0.7) return '#e6a23c'
  return '#f56c6c'
}

// 加载规则列表
const loadRuleList = async () => {
  loading.value = true
  try {
    // 临时模拟数据过滤
    let list = [...miningRuleList.value]
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
    miningRuleList.value = list.slice(start, end)
  } catch (error) {
    ElMessage.error('加载规则列表失败')
  } finally {
    loading.value = false
  }
}

// 查询
const handleQuery = () => {
  queryParams.page = 1
  loadRuleList()
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
  loadRuleList()
}

// 执行挖掘
const handleRunMining = () => {
  ElMessageBox.confirm(
    '确定要执行规则挖掘吗？会基于最近的标注数据自动挖掘新规则，执行时间可能较长！',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    loading.value = true
    try {
      // 模拟挖掘过程
      await new Promise(resolve => setTimeout(resolve, 2000))
      ElMessage.success('规则挖掘执行成功，共挖掘到3条新规则')
      loadRuleList()
    } catch (error) {
      ElMessage.error('规则挖掘执行失败')
    } finally {
      loading.value = false
    }
  })
}

// 通过规则
const handleApprove = (row: MiningRule) => {
  ElMessageBox.confirm(
    `确定要通过该规则吗？通过后规则将自动上线生效！`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 模拟API调用
      row.status = 'approved'
      ElMessage.success('规则已通过，已自动上线')
    } catch (error) {
      ElMessage.error('操作失败')
    }
  })
}

// 驳回规则
const handleReject = (row: MiningRule) => {
  ElMessageBox.prompt('请输入驳回原因', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '驳回原因不能为空'
  }).then(async ({ value }) => {
    try {
      // 模拟API调用
      row.status = 'rejected'
      ElMessage.success('规则已驳回')
    } catch (error) {
      ElMessage.error('操作失败')
    }
  })
}

onMounted(() => {
  loadRuleList()
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
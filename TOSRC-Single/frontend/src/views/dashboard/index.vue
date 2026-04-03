<template>
  <div class="dashboard-container">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="item in statCards" :key="item.key">
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-content">
            <div class="stat-left">
              <p class="stat-label">{{ item.label }}</p>
              <h3 class="stat-value">{{ item.value }}</h3>
              <p class="stat-desc" :class="item.trendClass">
                <el-icon><component :is="item.trendIcon" /></el-icon>
                {{ item.desc }}
              </p>
            </div>
            <div class="stat-icon" :style="{ backgroundColor: item.color }">
              <el-icon :size="32" color="#fff"><component :is="item.icon" /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="16">
        <el-card title="请求趋势" class="chart-card">
          <div ref="chartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card title="意图分布" class="chart-card">
          <div ref="pieChartRef" class="pie-chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近请求记录 -->
    <el-row class="mt-20">
      <el-col :span="24">
        <el-card title="最近请求记录">
          <el-table :data="recentRecords" border>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="text" label="用户文本" min-width="300" show-overflow-tooltip />
            <el-table-column prop="intent" label="识别意图" width="150" />
            <el-table-column prop="confidence" label="置信度" width="120">
              <template #default="{ row }">
                <el-tag :type="row.confidence >= 0.8 ? 'success' : 'warning'">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="时间" width="180" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { 
  Odometer, 
  Collection, 
  Grid, 
  Key, 
  ArrowUp, 
  ArrowDown 
} from '@element-plus/icons-vue'
// import { getStatsApi, getRecentRecordsApi } from '@/api/stats'

// 统计卡片数据
const statCards = ref([
  {
    key: 'total_requests',
    label: '总请求数',
    value: '1,234',
    desc: '较昨日 +12.5%',
    trendIcon: ArrowUp,
    trendClass: 'trend-up',
    icon: Odometer,
    color: '#409eff'
  },
  {
    key: 'total_intents',
    label: '意图数量',
    value: '36',
    desc: '较上周 +2',
    trendIcon: ArrowUp,
    trendClass: 'trend-up',
    icon: Collection,
    color: '#67c23a'
  },
  {
    key: 'total_entities',
    label: '实体数量',
    value: '18',
    desc: '较上周 0',
    trendIcon: Key,
    trendClass: 'trend-normal',
    icon: Grid,
    color: '#e6a23c'
  },
  {
    key: 'accuracy',
    label: '识别准确率',
    value: '96.8%',
    desc: '较昨日 -0.3%',
    trendIcon: ArrowDown,
    trendClass: 'trend-down',
    icon: Key,
    color: '#f56c6c'
  }
])

// 最近请求记录
const recentRecords = ref([
  { id: 1, text: '我要租个两室一厅，预算3000左右', intent: '租房咨询', confidence: 0.92, create_time: '2026-03-24 18:30:00' },
  { id: 2, text: '明天出门需要带伞吗', intent: '天气查询', confidence: 0.98, create_time: '2026-03-24 18:25:00' },
  { id: 3, text: '这个房子的租金太贵了', intent: '投诉', confidence: 0.87, create_time: '2026-03-24 18:20:00' },
  { id: 4, text: '建议你们增加更多的房源信息', intent: '建议', confidence: 0.91, create_time: '2026-03-24 18:15:00' },
  { id: 5, text: '你们的服务太好了，非常满意', intent: '表扬', confidence: 0.95, create_time: '2026-03-24 18:10:00' }
])

const chartRef = ref<HTMLElement>()
const pieChartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
let pieChartInstance: echarts.ECharts | null = null

// 初始化折线图
const initLineChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['请求量', '准确率']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    },
    yAxis: [
      {
        type: 'value',
        name: '请求量',
        position: 'left'
      },
      {
        type: 'value',
        name: '准确率',
        position: 'right',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      }
    ],
    series: [
      {
        name: '请求量',
        type: 'line',
        smooth: true,
        data: [120, 132, 101, 134, 90, 230, 210]
      },
      {
        name: '准确率',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: [96.5, 97.2, 95.8, 96.1, 96.8, 97.3, 96.9]
      }
    ]
  }

  chartInstance.setOption(option)
}

// 初始化饼图
const initPieChart = () => {
  if (!pieChartRef.value) return
  pieChartInstance = echarts.init(pieChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '意图分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '16',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 1048, name: '咨询' },
          { value: 735, name: '查询' },
          { value: 580, name: '投诉' },
          { value: 484, name: '建议' },
          { value: 300, name: '表扬' },
          { value: 200, name: '其他' }
        ]
      }
    ]
  }

  pieChartInstance.setOption(option)
}

// 自适应
const resizeCharts = () => {
  chartInstance?.resize()
  pieChartInstance?.resize()
}

onMounted(() => {
  initLineChart()
  initPieChart()
  window.addEventListener('resize', resizeCharts)
  
  // 后续替换为真实接口调用
  // loadStatsData()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  chartInstance?.dispose()
  pieChartInstance?.dispose()
})
</script>

<style scoped>
.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-left .stat-label {
  font-size: 14px;
  color: #909399;
  margin: 0 0 8px 0;
}

.stat-left .stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin: 0 0 8px 0;
}

.stat-left .stat-desc {
  font-size: 12px;
  margin: 0;
}

.trend-up {
  color: #67c23a;
}

.trend-down {
  color: #f56c6c;
}

.trend-normal {
  color: #909399;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-card {
  height: 400px;
}

.chart-container {
  width: 100%;
  height: 320px;
}

.pie-chart-container {
  width: 100%;
  height: 320px;
}
</style>
<template>
  <div class="page-container">
    <el-tabs v-model="activeTab" class="config-tabs">
      <el-tab-pane label="基础配置" name="base">
        <el-card>
          <el-form
            ref="baseFormRef"
            :model="baseConfig"
            :rules="baseFormRules"
            label-width="180px"
            class="config-form"
          >
            <el-form-item label="系统名称" prop="system_name">
              <el-input v-model="baseConfig.system_name" style="width: 400px" />
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input
                v-model="baseConfig.system_description"
                type="textarea"
                :rows="3"
                style="width: 400px"
              />
            </el-form-item>
            <el-form-item label="默认识别阈值">
              <el-slider
                v-model="baseConfig.default_threshold"
                :min="0"
                :max="100"
                :step="1"
                show-input
                style="width: 400px"
              />
              <div class="form-tip">低于该阈值的识别结果会自动调用LLM进行二次识别</div>
            </el-form-item>
            <el-form-item label="自动规则挖掘">
              <el-switch
                v-model="baseConfig.auto_mining_enabled"
                active-text="开启"
                inactive-text="关闭"
              />
              <div class="form-tip">开启后系统会自动从标注数据中挖掘新规则</div>
            </el-form-item>
            <el-form-item label="规则自动上线">
              <el-switch
                v-model="baseConfig.auto_approve_rules"
                active-text="开启"
                inactive-text="关闭"
              />
              <div class="form-tip">开启后挖掘到的规则置信度达到阈值时自动上线，无需人工审核</div>
            </el-form-item>
            <el-form-item label="自动上线阈值">
              <el-slider
                v-model="baseConfig.auto_approve_threshold"
                :min="0"
                :max="100"
                :step="1"
                show-input
                :disabled="!baseConfig.auto_approve_rules"
                style="width: 400px"
              />
            </el-form-item>
            <el-form-item label="规则包热重载">
              <el-switch
                v-model="baseConfig.rule_hot_reload"
                active-text="开启"
                inactive-text="关闭"
              />
              <div class="form-tip">开启后规则包文件修改后自动重载，无需重启服务</div>
            </el-form-item>
            <el-form-item label="默认LLM模型">
              <el-select v-model="baseConfig.default_llm" style="width: 400px">
                <el-option label="DeepSeek" value="deepseek" />
                <el-option label="火山引擎豆包" value="doubao" />
                <el-option label="通义千问" value="qwen" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveBaseConfig" :loading="baseSaving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="API配置" name="api">
        <el-card>
          <el-form
            ref="apiFormRef"
            :model="apiConfig"
            :rules="apiFormRules"
            label-width="180px"
            class="config-form"
          >
            <el-form-item label="DeepSeek API Key" prop="deepseek_api_key">
              <el-input
                v-model="apiConfig.deepseek_api_key"
                type="password"
                show-password
                placeholder="请输入DeepSeek API Key"
                style="width: 400px"
              />
            </el-form-item>
            <el-form-item label="DeepSeek API地址">
              <el-input
                v-model="apiConfig.deepseek_api_url"
                placeholder="https://api.deepseek.com"
                style="width: 400px"
              />
            </el-form-item>
            <el-form-item label="火山引擎API Key" prop="volcengine_api_key">
              <el-input
                v-model="apiConfig.volcengine_api_key"
                type="password"
                show-password
                placeholder="请输入火山引擎API Key"
                style="width: 400px"
              />
            </el-form-item>
            <el-form-item label="API请求超时时间">
              <el-input-number
                v-model="apiConfig.api_timeout"
                :min="1000"
                :max="60000"
                :step="1000"
                style="width: 200px"
              />
              <span class="ml-10">毫秒</span>
            </el-form-item>
            <el-form-item label="请求限流阈值">
              <el-input-number
                v-model="apiConfig.rate_limit"
                :min="1"
                :max="10000"
                style="width: 200px"
              />
              <span class="ml-10">次/分钟</span>
            </el-form-item>
            <el-form-item label="启用API日志">
              <el-switch
                v-model="apiConfig.api_log_enabled"
                active-text="开启"
                inactive-text="关闭"
              />
              <div class="form-tip">开启后所有API请求都会记录日志</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveApiConfig" :loading="apiSaving">保存配置</el-button>
              <el-button @click="testApiConnection" :loading="testLoading" class="ml-10">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="存储配置" name="storage">
        <el-card>
          <el-form
            ref="storageFormRef"
            :model="storageConfig"
            label-width="180px"
            class="config-form"
          >
            <el-form-item label="数据库类型">
              <el-select v-model="storageConfig.db_type" disabled style="width: 200px">
                <el-option label="SQLite" value="sqlite" />
              </el-select>
              <div class="form-tip">单租户版本仅支持SQLite数据库</div>
            </el-form-item>
            <el-form-item label="数据库路径">
              <el-input v-model="storageConfig.db_path" disabled style="width: 400px" />
            </el-form-item>
            <el-form-item label="自动备份">
              <el-switch
                v-model="storageConfig.auto_backup"
                active-text="开启"
                inactive-text="关闭"
              />
            </el-form-item>
            <el-form-item label="备份周期">
              <el-select
                v-model="storageConfig.backup_cycle"
                :disabled="!storageConfig.auto_backup"
                style="width: 200px"
              >
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
            </el-form-item>
            <el-form-item label="备份保留天数">
              <el-input-number
                v-model="storageConfig.backup_retention_days"
                :min="1"
                :max="365"
                :disabled="!storageConfig.auto_backup"
                style="width: 200px"
              />
              <span class="ml-10">天</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveStorageConfig" :loading="storageSaving">保存配置</el-button>
              <el-button @click="manualBackup" class="ml-10">手动备份</el-button>
              <el-button @click="restoreBackup" type="warning" class="ml-10">恢复备份</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElForm, ElMessageBox } from 'element-plus'

const activeTab = ref('base')
const baseFormRef = ref<InstanceType<typeof ElForm>>()
const apiFormRef = ref<InstanceType<typeof ElForm>>()
const storageFormRef = ref<InstanceType<typeof ElForm>>()

const baseSaving = ref(false)
const apiSaving = ref(false)
const storageSaving = ref(false)
const testLoading = ref(false)

// 基础配置
const baseConfig = reactive({
  system_name: 'TOSRC 语义路由调度引擎',
  system_description: '专注于本地语义识别、策略化路由、插件化场景适配的智能路由引擎',
  default_threshold: 70,
  auto_mining_enabled: true,
  auto_approve_rules: false,
  auto_approve_threshold: 90,
  rule_hot_reload: true,
  default_llm: 'deepseek'
})

// API配置
const apiConfig = reactive({
  deepseek_api_key: '',
  deepseek_api_url: 'https://api.deepseek.com',
  volcengine_api_key: '',
  api_timeout: 30000,
  rate_limit: 1000,
  api_log_enabled: true
})

// 存储配置
const storageConfig = reactive({
  db_type: 'sqlite',
  db_path: './data/tosrc.db',
  auto_backup: true,
  backup_cycle: 'daily',
  backup_retention_days: 30
})

// 表单校验规则
const baseFormRules = {
  system_name: [
    { required: true, message: '请输入系统名称', trigger: 'blur' }
  ]
}

const apiFormRules = {
  deepseek_api_key: [
    { required: true, message: '请输入DeepSeek API Key', trigger: 'blur' }
  ],
  volcengine_api_key: [
    { required: false, message: '请输入火山引擎API Key', trigger: 'blur' }
  ]
}

// 保存基础配置
const saveBaseConfig = () => {
  if (!baseFormRef.value) return
  
  baseFormRef.value.validate(async (valid) => {
    if (valid) {
      baseSaving.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success('基础配置保存成功')
      } catch (error) {
        ElMessage.error('保存失败')
      } finally {
        baseSaving.value = false
      }
    }
  })
}

// 保存API配置
const saveApiConfig = () => {
  if (!apiFormRef.value) return
  
  apiFormRef.value.validate(async (valid) => {
    if (valid) {
      apiSaving.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success('API配置保存成功')
      } catch (error) {
        ElMessage.error('保存失败')
      } finally {
        apiSaving.value = false
      }
    }
  })
}

// 测试API连接
const testApiConnection = () => {
  testLoading.value = true
  try {
    // 模拟API调用
    setTimeout(() => {
      ElMessage.success('API连接测试成功')
      testLoading.value = false
    }, 2000)
  } catch (error) {
    ElMessage.error('API连接测试失败')
    testLoading.value = false
  }
}

// 保存存储配置
const saveStorageConfig = () => {
  storageSaving.value = true
  try {
    // 模拟API调用
    setTimeout(() => {
      ElMessage.success('存储配置保存成功')
      storageSaving.value = false
    }, 1000)
  } catch (error) {
    ElMessage.error('保存失败')
    storageSaving.value = false
  }
}

// 手动备份
const manualBackup = () => {
  ElMessageBox.confirm(
    '确定要执行手动备份吗？会自动备份当前所有数据到备份目录！',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 模拟备份过程
      await new Promise(resolve => setTimeout(resolve, 2000))
      ElMessage.success('手动备份完成，备份文件已保存到backup目录')
    } catch (error) {
      ElMessage.error('备份失败')
    }
  })
}

// 恢复备份
const restoreBackup = () => {
  ElMessageBox.confirm(
    '确定要恢复备份吗？恢复操作会覆盖当前所有数据，请谨慎操作！',
    '警告',
    {
      confirmButtonText: '确定恢复',
      cancelButtonText: '取消',
      type: 'danger'
    }
  ).then(async () => {
    try {
      // 模拟恢复过程
      await new Promise(resolve => setTimeout(resolve, 3000))
      ElMessage.success('备份恢复成功，系统将自动重启')
    } catch (error) {
      ElMessage.error('恢复失败')
    }
  })
}
</script>

<style scoped>
.page-container {
  width: 100%;
}

.config-tabs {
  width: 100%;
}

.config-form {
  padding: 20px 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.ml-10 {
  margin-left: 10px;
}
</style>
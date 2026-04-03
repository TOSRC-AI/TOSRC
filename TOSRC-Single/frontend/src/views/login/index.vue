<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h2>TOSRC 管理后台</h2>
        <p>语义路由调度引擎</p>
      </div>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        label-width="0px"
      >
        <el-form-item prop="apiKey">
          <el-input
            v-model="loginForm.apiKey"
            type="password"
            placeholder="请输入管理员API Key"
            size="large"
            prefix-icon="Key"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
        <div class="login-tips">
          <p>默认API Key：admin-llm-router-2026</p>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElForm, ElMessage } from 'element-plus'
import { Key } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const loginFormRef = ref<InstanceType<typeof ElForm>>()
const loading = ref(false)

// 表单数据
const loginForm = reactive({
  apiKey: ''
})

// 表单校验规则
const loginRules = {
  apiKey: [
    { required: true, message: '请输入API Key', trigger: 'blur' },
    { min: 10, message: 'API Key长度不能少于10位', trigger: 'blur' }
  ]
}

// 登录
const handleLogin = () => {
  if (!loginFormRef.value) return
  
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const success = await userStore.login(loginForm.apiKey)
        if (success) {
          ElMessage.success('登录成功')
          router.push('/dashboard')
        } else {
          ElMessage.error('API Key无效，请重新输入')
        }
      } catch (error) {
        ElMessage.error('登录失败，请检查API Key是否正确')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-box {
  width: 400px;
  background-color: #fff;
  border-radius: 8px;
  padding: 40px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.login-header h2 {
  color: #303133;
  font-size: 28px;
  margin: 0 0 10px 0;
}

.login-header p {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.login-form {
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
}

.login-tips {
  text-align: center;
  color: #909399;
  font-size: 12px;
}

.login-tips p {
  margin: 0;
}
</style>
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { loginApi, logoutApi } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref({
    username: '管理员',
    role: 'admin'
  })

  // 登录
  const login = async (apiKey: string) => {
    // 调用登录接口
    const res = await loginApi(apiKey)
    if (res.code === 0) {
      token.value = apiKey
      localStorage.setItem('token', apiKey)
      return true
    }
    return false
  }

  // 退出登录
  const logout = () => {
    token.value = ''
    localStorage.removeItem('token')
    // 调用退出接口
    logoutApi()
  }

  return {
    token,
    userInfo,
    login,
    logout
  }
})
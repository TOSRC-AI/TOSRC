import request from '@/utils/request'

// 登录API（验证API Key是否有效）
export const loginApi = (apiKey: string) => {
  // 验证API Key可以调用一个需要权限的接口来测试，比如获取意图列表
  return request({
    url: '/v1/admin/intent/list',
    method: 'get',
    headers: {
      'X-Admin-Api-Key': apiKey
    }
  })
}

// 退出登录API
export const logoutApi = () => {
  // 前端清除token即可，无需调用后端接口
  return Promise.resolve({ code: 0, message: 'success' })
}
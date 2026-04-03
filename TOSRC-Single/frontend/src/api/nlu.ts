import request from '@/utils/request'

// 意图相关API
export interface Intent {
  intent_id: number
  intent_code: string
  intent_name: string
  parent_id: number
  level: number
  priority: number
  is_enabled: boolean
  description: string
  children?: Intent[]
}

export interface IntentForm {
  intent_id?: number
  intent_code: string
  intent_name: string
  parent_id: number
  level?: number
  priority: number
  is_enabled: boolean
  description: string
}

// 获取意图列表
export const getIntentListApi = () => {
  return request({
    url: '/v1/admin/intent/list',
    method: 'get'
  })
}

// 新增意图
export const addIntentApi = (data: IntentForm) => {
  return request({
    url: '/v1/admin/intent/add',
    method: 'post',
    data
  })
}

// 更新意图
export const updateIntentApi = (data: IntentForm) => {
  return request({
    url: '/v1/admin/intent/update',
    method: 'post',
    data
  })
}

// 删除意图
export const deleteIntentApi = (intent_id: number) => {
  return request({
    url: `/v1/admin/intent/delete/${intent_id}`,
    method: 'post'
  })
}

// 关键词相关API
export interface Keyword {
  keyword_id: number
  keyword: string
  type: string
  relation_id: number
  weight: number
  is_enabled: boolean
  description: string
}

export interface KeywordForm {
  keyword_id?: number
  keyword: string
  type: string
  relation_id: number
  weight: number
  is_enabled: boolean
  description: string
}

// 获取关键词列表
export const getKeywordListApi = (params?: {
  type?: string
  relation_id?: number
  keyword?: string
  page?: number
  page_size?: number
}) => {
  return request({
    url: '/v1/admin/keyword/list',
    method: 'get',
    params
  })
}

// 新增关键词
export const addKeywordApi = (data: KeywordForm) => {
  return request({
    url: '/v1/admin/keyword/add',
    method: 'post',
    data
  })
}

// 更新关键词
export const updateKeywordApi = (data: KeywordForm) => {
  return request({
    url: '/v1/admin/keyword/update',
    method: 'post',
    data
  })
}

// 删除关键词
export const deleteKeywordApi = (keyword_id: number) => {
  return request({
    url: `/v1/admin/keyword/delete/${keyword_id}`,
    method: 'post'
  })
}

// 规则包相关API
export interface RulePackage {
  scene: string
  scene_name: string
  entity_rule_count: number
  intent_rule_count: number
  emotion_rule_count: number
  negative_rule_count: number
  last_modify_time: number
  file_path: string
}

// 获取规则包列表
export const getRulePackageListApi = () => {
  return request({
    url: '/v1/admin/rule/packages',
    method: 'get'
  })
}

// 获取规则包详情
export const getRulePackageDetailApi = (scene: string) => {
  return request({
    url: `/v1/admin/rule/package/${scene}`,
    method: 'get'
  })
}

// 重载规则包
export const reloadRulePackageApi = (scene: string) => {
  return request({
    url: `/v1/admin/rule/reload/${scene}`,
    method: 'post'
  })
}

// 上传规则包
export const uploadRulePackageApi = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/v1/admin/rule/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: {
      title: '登录',
      noAuth: true
    }
  },
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: {
          title: '控制台',
          icon: 'Odometer'
        }
      },
      {
        path: 'nlu',
        name: 'NLU',
        meta: {
          title: '语义管理',
          icon: 'Collection'
        },
        children: [
          {
            path: 'intent',
            name: 'Intent',
            component: () => import('@/views/nlu/intent.vue'),
            meta: {
              title: '意图管理'
            }
          },
          {
            path: 'entity',
            name: 'Entity',
            component: () => import('@/views/nlu/entity.vue'),
            meta: {
              title: '实体管理'
            }
          },
          {
            path: 'keyword',
            name: 'Keyword',
            component: () => import('@/views/nlu/keyword.vue'),
            meta: {
              title: '关键词管理'
            }
          }
        ]
      },
      {
        path: 'rule',
        name: 'Rule',
        meta: {
          title: '规则管理',
          icon: 'Grid'
        },
        children: [
          {
            path: 'package',
            name: 'RulePackage',
            component: () => import('@/views/rule/package.vue'),
            meta: {
              title: '规则包管理'
            }
          },
          {
            path: 'miner',
            name: 'RuleMiner',
            component: () => import('@/views/rule/miner.vue'),
            meta: {
              title: '规则挖掘'
            }
          }
        ]
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('@/views/stats/index.vue'),
        meta: {
          title: '统计分析',
          icon: 'DataAnalysis'
        }
      },
      {
        path: 'plugin',
        name: 'Plugin',
        component: () => import('@/views/plugin/index.vue'),
        meta: {
          title: '插件管理',
          icon: 'Paperclip'
        }
      },
      {
        path: 'system',
        name: 'System',
        meta: {
          title: '系统管理',
          icon: 'Setting'
        },
        children: [
          {
            path: 'config',
            name: 'SystemConfig',
            component: () => import('@/views/system/config.vue'),
            meta: {
              title: '系统配置'
            }
          },
          {
            path: 'log',
            name: 'SystemLog',
            component: () => import('@/views/system/log.vue'),
            meta: {
              title: '操作日志'
            }
          }
        ]
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const token = userStore.token
  
  // 不需要登录的页面
  if (to.meta.noAuth) {
    next()
    return
  }
  
  // 没有token跳转到登录页
  if (!token) {
    next('/login')
    return
  }
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - TOSRC管理后台` : 'TOSRC管理后台'
  next()
})

export default router
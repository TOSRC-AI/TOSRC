<template>
  <div class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <h2>TOSRC</h2>
        <p>语义路由调度引擎</p>
      </div>
      <el-menu
        :default-active="activeMenu"
        :router="true"
        mode="vertical"
        :collapse="isCollapse"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <template v-for="route in menuRoutes" :key="route.path">
          <!-- 一级菜单无子路由 -->
          <el-menu-item v-if="!route.children" :index="route.path">
            <el-icon><component :is="route.meta.icon" /></el-icon>
            <template #title>{{ route.meta.title }}</template>
          </el-menu-item>
          
          <!-- 有子路由的菜单 -->
          <el-sub-menu v-else :index="route.path">
            <template #title>
              <el-icon><component :is="route.meta.icon" /></el-icon>
              <span>{{ route.meta.title }}</span>
            </template>
            <el-menu-item
              v-for="child in route.children"
              :key="child.path"
              :index="`/${route.path}/${child.path}`"
            >
              {{ child.meta.title }}
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-aside>

    <!-- 右侧主区域 -->
    <div class="main-container">
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-if="isCollapse" />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="item in breadcrumbList" :key="item.path">
              {{ item.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              <span>管理员</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="config">系统设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  Fold, 
  Expand, 
  User, 
  ArrowDown,
  Odometer,
  Collection,
  Grid,
  DataAnalysis,
  Paperclip,
  Setting
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const activeMenu = ref('')

// 菜单路由配置（和router对应）
const menuRoutes = [
  {
    path: '/dashboard',
    meta: {
      title: '控制台',
      icon: Odometer
    }
  },
  {
    path: 'nlu',
    meta: {
      title: '语义管理',
      icon: Collection
    },
    children: [
      { path: 'intent', meta: { title: '意图管理' } },
      { path: 'entity', meta: { title: '实体管理' } },
      { path: 'keyword', meta: { title: '关键词管理' } }
    ]
  },
  {
    path: 'rule',
    meta: {
      title: '规则管理',
      icon: Grid
    },
    children: [
      { path: 'package', meta: { title: '规则包管理' } },
      { path: 'miner', meta: { title: '规则挖掘' } }
    ]
  },
  {
    path: '/stats',
    meta: {
      title: '统计分析',
      icon: DataAnalysis
    }
  },
  {
    path: '/plugin',
    meta: {
      title: '插件管理',
      icon: Paperclip
    }
  },
  {
    path: 'system',
    meta: {
      title: '系统管理',
      icon: Setting
    },
    children: [
      { path: 'config', meta: { title: '系统配置' } },
      { path: 'log', meta: { title: '操作日志' } }
    ]
  }
]

// 面包屑导航
const breadcrumbList = computed(() => {
  const matched = route.matched.filter(item => item.meta && item.meta.title)
  return matched
})

// 激活的菜单
onMounted(() => {
  activeMenu.value = route.path
})

// 处理下拉菜单事件
const handleCommand = (command: string) => {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      userStore.logout()
      ElMessage.success('退出登录成功')
      router.push('/login')
    }).catch(() => {})
  }
}
</script>

<style scoped>
.layout-container {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
  height: 100vh;
  overflow: hidden;
}

.logo {
  height: 60px;
  padding: 10px 0;
  text-align: center;
  border-bottom: 1px solid #263446;
}

.logo h2 {
  color: #fff;
  font-size: 20px;
  margin: 0;
  line-height: 30px;
}

.logo p {
  color: #909399;
  font-size: 12px;
  margin: 0;
  line-height: 20px;
}

:deep(.el-menu) {
  border-right: none;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #f0f2f5;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 1px 4px rgba(0, 21, 41, .08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #606266;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

/* 页面过渡动画 */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
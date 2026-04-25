<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside
      v-if="authStore.isLoggedIn"
      width="220px"
      class="layout-sidebar"
    >
      <div class="sidebar-logo">
        <el-icon><Promotion /></el-icon>
        <span>E-Parking</span>
      </div>

      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
        background-color="#1a1a2e"
        text-color="#b0b3c7"
        active-text-color="#67c23a"
      >
        <el-menu-item index="/">
          <el-icon><Money /></el-icon>
          <span>POS</span>
        </el-menu-item>

        <el-menu-item index="/gate-in">
          <el-icon><ArrowRight /></el-icon>
          <span>Gate In</span>
        </el-menu-item>

        <el-menu-item index="/transaksi">
          <el-icon><Document /></el-icon>
          <span>Transaksi</span>
        </el-menu-item>

        <el-menu-item index="/member">
          <el-icon><User /></el-icon>
          <span>Member</span>
        </el-menu-item>

        <el-menu-item index="/report">
          <el-icon><DataLine /></el-icon>
          <span>Laporan</span>
        </el-menu-item>

        <el-menu-item index="/notification">
          <el-icon><Bell /></el-icon>
          <span>Notifikasi</span>
        </el-menu-item>

        <el-sub-menu v-if="authStore.isAdmin" index="/admin">
          <template #title>
            <el-icon><Tools /></el-icon>
            <span>Admin</span>
          </template>
          <el-menu-item index="/setting">Pengaturan</el-menu-item>
          <el-menu-item index="/device">Perangkat</el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div class="sidebar-footer">
        <el-button type="danger" plain size="small" class="w-full" @click="logout">
          <el-icon><SwitchButton /></el-icon>
          Keluar
        </el-button>
      </div>
    </el-aside>

    <!-- Main area -->
    <el-container class="layout-main-area">
      <!-- Header (only when logged in) -->
      <el-header v-if="authStore.isLoggedIn" class="layout-header" height="56px">
        <div class="header-breadcrumb">
          <el-breadcrumb>
            <el-breadcrumb-item>{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-user">
          <el-tag :type="authStore.isAdmin ? 'danger' : 'primary'" size="small" class="mr-2">
            {{ authStore.user?.role }}
          </el-tag>
          <span class="username">{{ authStore.user?.username }}</span>
        </div>
      </el-header>

      <!-- Main content -->
      <el-main class="layout-main">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import {
  Promotion,
  Money,
  ArrowRight,
  Document,
  User,
  DataLine,
  Bell,
  Tools,
  SwitchButton,
} from '@element-plus/icons-vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const pageTitle = computed(() => {
  const titles = {
    '/': 'POS — Gate Out',
    '/gate-in': 'Gate In Monitor',
    '/transaksi': 'Transaksi',
    '/setting': 'Pengaturan',
    '/device': 'Perangkat',
    '/member': 'Member',
    '/report': 'Laporan',
    '/notification': 'Notifikasi',
    '/login': 'Login',
  }
  return titles[route.path] || 'E-Parking'
})

async function logout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  display: flex;
}

.layout-sidebar {
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar-logo .el-icon {
  font-size: 22px;
  color: #67c23a;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.layout-main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.layout-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  z-index: 1;
}

.header-user {
  display: flex;
  align-items: center;
}

.username {
  font-size: 14px;
  color: #606266;
}

.layout-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>

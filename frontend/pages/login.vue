<template>
  <div class="login-page flex items-center justify-center">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="text-center">
          <el-icon class="login-logo"><Promotion /></el-icon>
          <h2 class="login-title">E-Parking v2</h2>
          <p class="login-subtitle">Silakan masuk untuk melanjutkan</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @keyup.enter="handleLogin"
      >
        <el-form-item label="Username" prop="username">
          <el-input
            v-model="form.username"
            placeholder="Masukkan username"
            :prefix-icon="User"
            size="large"
            clearable
            autofocus
          />
        </el-form-item>

        <el-form-item label="Password" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="Masukkan password"
            :prefix-icon="Lock"
            size="large"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="w-full"
            :loading="authStore.isLoading"
            @click="handleLogin"
          >
            Masuk
          </el-button>
        </el-form-item>

        <el-alert
          v-if="authStore.error"
          :title="authStore.error"
          type="error"
          show-icon
          :closable="false"
          class="mt-2"
        />
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock, Promotion } from '@element-plus/icons-vue'

definePageMeta({
  layout: false,
  middleware: 'auth',
})

const authStore = useAuthStore()
const router = useRouter()
const formRef = ref()

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [
    { required: true, message: 'Username wajib diisi', trigger: 'blur' },
  ],
  password: [
    { required: true, message: 'Password wajib diisi', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('Login berhasil')
    router.push('/')
  } catch (err) {
    // Error is already stored in authStore.error
    ElMessage.error(err.message || 'Login gagal')
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.login-card {
  width: 400px;
  max-width: 90vw;
}

.login-logo {
  font-size: 48px;
  color: #67c23a;
  margin-bottom: 12px;
}

.login-title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
}

.login-subtitle {
  margin: 0;
  font-size: 14px;
  color: #909399;
}
</style>

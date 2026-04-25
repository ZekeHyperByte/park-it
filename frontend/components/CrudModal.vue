<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="600px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-position="top"
      @submit.prevent
    >
      <el-form-item
        v-for="field in fields"
        :key="field.prop"
        :label="field.label"
        :prop="field.prop"
      >
        <!-- Text / Number input -->
        <el-input
          v-if="field.type === 'text' || field.type === 'number'"
          v-model="formData[field.prop]"
          :type="field.inputType || 'text'"
          :placeholder="field.placeholder || ''"
          :disabled="field.disabled"
          clearable
        />

        <!-- Textarea -->
        <el-input
          v-else-if="field.type === 'textarea'"
          v-model="formData[field.prop]"
          type="textarea"
          :rows="field.rows || 3"
          :placeholder="field.placeholder || ''"
          :disabled="field.disabled"
        />

        <!-- Select / Enum -->
        <el-select
          v-else-if="field.type === 'select'"
          v-model="formData[field.prop]"
          :placeholder="field.placeholder || ''"
          :disabled="field.disabled"
          style="width: 100%"
        >
          <el-option
            v-for="opt in field.options"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <!-- Switch / Boolean -->
        <el-switch
          v-else-if="field.type === 'boolean'"
          v-model="formData[field.prop]"
          :disabled="field.disabled"
          active-text="Ya"
          inactive-text="Tidak"
        />

        <!-- Time picker -->
        <el-time-picker
          v-else-if="field.type === 'time'"
          v-model="formData[field.prop]"
          :placeholder="field.placeholder || ''"
          :disabled="field.disabled"
          format="HH:mm"
          value-format="HH:mm:ss"
          style="width: 100%"
        />

        <!-- Date picker -->
        <el-date-picker
          v-else-if="field.type === 'date'"
          v-model="formData[field.prop]"
          type="date"
          :placeholder="field.placeholder || ''"
          :disabled="field.disabled"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />

        <!-- Password -->
        <el-input
          v-else-if="field.type === 'password'"
          v-model="formData[field.prop]"
          type="password"
          :placeholder="field.placeholder || ''"
          :disabled="field.disabled"
          show-password
          clearable
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">Batal</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        Simpan
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'Form' },
  fields: { type: Array, required: true },
  initialData: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const formRef = ref()
const formData = reactive({})

// Build validation rules from fields
const formRules = computed(() => {
  const rules = {}
  for (const field of props.fields) {
    if (field.required) {
      rules[field.prop] = [
        { required: true, message: `${field.label} wajib diisi`, trigger: 'blur' },
      ]
      if (field.minLength) {
        rules[field.prop].push({
          min: field.minLength,
          message: `Minimal ${field.minLength} karakter`,
          trigger: 'blur',
        })
      }
    }
    if (field.type === 'number') {
      rules[field.prop] = rules[field.prop] || []
      rules[field.prop].push({
        type: 'number',
        message: 'Harus berupa angka',
        trigger: 'blur',
      })
    }
  }
  return rules
})

// Reset form when opening
watch(
  () => props.modelValue,
  async (val) => {
    if (val) {
      await nextTick()
      formRef.value?.resetFields?.()
      // Populate initial data
      for (const field of props.fields) {
        formData[field.prop] = props.initialData[field.prop] ?? (field.type === 'boolean' ? false : '')
      }
    }
  },
  { immediate: true }
)

function handleClose() {
  visible.value = false
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  emit('submit', { ...formData })
}
</script>

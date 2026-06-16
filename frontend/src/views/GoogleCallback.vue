<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { completeGoogleLogin } from '../composables/useAuth'

const router = useRouter()
const error  = ref('')

onMounted(() => {
  // The backend delivers the platform JWT in the URL fragment (never sent to a
  // server, never logged): /google-callback#token=<jwt>
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
  if (!token) {
    error.value = 'Google sign-in failed. Please try again.'
    setTimeout(() => router.replace('/login'), 1800)
    return
  }
  completeGoogleLogin(token)
  // Clear the token from the address bar before navigating on.
  history.replaceState(null, '', '/google-callback')
  router.replace('/overview')
})
</script>

<template>
  <div class="google-callback">
    <p class="t-tertiary">{{ error || 'Signing you in…' }}</p>
  </div>
</template>

<style scoped>
.google-callback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}
</style>

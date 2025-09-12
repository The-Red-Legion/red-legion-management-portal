<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <img src="/red-legion-logo.png" alt="Red Legion" class="mx-auto h-24 w-24 mb-6" />
        <h2 class="text-3xl font-bold text-red-legion-500 mb-2">Red Legion Payroll</h2>
        <p class="text-space-gray-400 mb-8">
          Web interface for Discord bot payroll system
        </p>
      </div>

      <div class="bg-space-gray-800 rounded-lg shadow-xl p-8">
        <div class="text-center space-y-6">
          <div>
            <h3 class="text-xl font-semibold text-white mb-2">Login Required</h3>
            <p class="text-space-gray-400 text-sm">
              Sign in with your Discord account to access the payroll system
            </p>
          </div>

          <button
            @click="loginWithDiscord"
            :disabled="loading"
            class="w-full flex items-center justify-center px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white font-medium rounded-lg transition-colors"
          >
            <svg v-if="!loading" class="w-5 h-5 mr-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419-.0189 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1568 2.4189Z"/>
            </svg>
            <div v-if="loading" class="w-5 h-5 mr-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            {{ loading ? 'Redirecting...' : 'Login with Discord' }}
          </button>

          <div class="text-xs text-space-gray-500">
            <p>Same authentication as the Discord bot</p>
            <p>No additional permissions required</p>
          </div>
        </div>
      </div>

      <div class="text-center text-space-gray-500 text-sm">
        <p>New to Red Legion? Contact an admin in Discord</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'LoginPage',
  emits: ['login'],
  setup(props, { emit }) {
    const loading = ref(false)

    const loginWithDiscord = () => {
      loading.value = true
      // Redirect to Discord OAuth via backend
      window.location.href = 'http://localhost:8000/auth/login'
    }

    return {
      loading,
      loginWithDiscord
    }
  }
}
</script>
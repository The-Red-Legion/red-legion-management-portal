<template>
  <div class="min-h-screen bg-space-gray-900 flex items-center justify-center px-4">
    <div class="max-w-md w-full">
      <!-- Logo and Title -->
      <div class="text-center mb-8">
        <div class="flex justify-center mb-6">
          <img src="/red-legion-logo.png" alt="Red Legion" class="h-20 w-20" />
        </div>
        <h1 class="text-3xl font-bold text-red-legion-500 mb-2">Red Legion</h1>
        <h2 class="text-xl text-space-gray-300">You've been logged out</h2>
      </div>

      <!-- Confirmation Card -->
      <div class="bg-space-gray-800 rounded-lg shadow-xl p-8">
        <div class="text-center mb-6">
          <!-- Success Icon -->
          <div class="mx-auto w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
          </div>
          
          <h3 class="text-lg font-semibold text-white mb-2">Successfully Logged Out</h3>
          <p class="text-space-gray-300 text-sm">
            You have been securely logged out of Red Legion Payroll. 
            Your session has been terminated and all local data cleared.
          </p>
        </div>

        <!-- Action Buttons -->
        <div class="space-y-3">
          <!-- Login with Discord Button -->
          <button
            @click="loginWithDiscord"
            class="w-full bg-discord-blue hover:bg-discord-blue-dark px-6 py-3 rounded-lg 
                   text-white font-medium flex items-center justify-center space-x-3 
                   transition-colors duration-200"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
            </svg>
            <span>Login with Discord</span>
          </button>

          <!-- Secondary Actions -->
          <div class="flex space-x-3">
            <button
              @click="$router.push('/')"
              class="flex-1 bg-space-gray-700 hover:bg-space-gray-600 px-4 py-2 rounded-lg 
                     text-space-gray-300 hover:text-white transition-colors duration-200 
                     text-sm font-medium"
            >
              Visit Homepage
            </button>
            
            <button
              @click="clearDataAndReload"
              class="flex-1 bg-red-legion-600 hover:bg-red-legion-700 px-4 py-2 rounded-lg 
                     text-white transition-colors duration-200 text-sm font-medium"
            >
              Clear All Data
            </button>
          </div>
        </div>

        <!-- Additional Info -->
        <div class="mt-6 pt-6 border-t border-space-gray-700">
          <div class="text-xs text-space-gray-400 text-center space-y-1">
            <p>Need help? Contact your Red Legion administrator</p>
            <p>Session expired: {{ new Date().toLocaleString() }}</p>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="text-center mt-8">
        <p class="text-xs text-space-gray-500">
          &copy; 2024 Red Legion. Secure Discord Bot Payroll System.
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'LogoutConfirmation',
  setup() {
    const router = useRouter()

    const loginWithDiscord = () => {
      // Redirect to Discord OAuth
      window.location.href = 'http://localhost:8000/auth/login'
    }

    const clearDataAndReload = () => {
      // Clear all localStorage data
      localStorage.clear()
      sessionStorage.clear()
      
      // Show confirmation
      alert('All local data has been cleared.')
      
      // Reload the page
      window.location.reload()
    }

    onMounted(() => {
      // Clear any existing user data
      localStorage.removeItem('red_legion_user')
      sessionStorage.clear()
      
      // Log the logout event
      console.log('User logged out at:', new Date().toISOString())
    })

    return {
      loginWithDiscord,
      clearDataAndReload
    }
  }
}
</script>

<style scoped>
/* Discord Brand Colors */
.bg-discord-blue {
  background-color: #5865F2;
}

.bg-discord-blue:hover,
.bg-discord-blue-dark {
  background-color: #4752C4;
}

/* Space theme colors - ensure these match your tailwind config */
.bg-space-gray-900 {
  background-color: #0f172a;
}

.bg-space-gray-800 {
  background-color: #1e293b;
}

.bg-space-gray-700 {
  background-color: #334155;
}

.bg-space-gray-600 {
  background-color: #475569;
}

.text-space-gray-300 {
  color: #cbd5e1;
}

.text-space-gray-400 {
  color: #94a3b8;
}

.text-space-gray-500 {
  color: #64748b;
}

.border-space-gray-700 {
  border-color: #334155;
}

.text-red-legion-500 {
  color: #ef4444;
}

.bg-red-legion-600 {
  background-color: #dc2626;
}

.bg-red-legion-700 {
  background-color: #b91c1c;
}
</style>
<template>
  <div id="app" class="min-h-screen bg-space-gray-900 text-white">
    <!-- Header -->
    <header class="bg-space-gray-800 shadow-lg">
      <div class="max-w-7xl mx-auto px-4 py-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <img src="/static/red-legion-logo.png" alt="Red Legion" class="h-12 w-12" />
            <h1 class="text-2xl font-bold text-red-legion-500">Red Legion Payroll</h1>
          </div>
          <div v-if="user" class="flex items-center space-x-4">
            <span class="text-space-gray-300">Welcome, {{ user.username }}</span>
            <button 
              @click="logout" 
              class="bg-red-legion-600 hover:bg-red-legion-700 px-4 py-2 rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8">
      <LoginPage v-if="!user" @login="handleLogin" />
      <PayrollWizard v-else :user="user" />
    </main>

    <!-- Footer -->
    <footer class="bg-space-gray-800 mt-12">
      <div class="max-w-7xl mx-auto px-4 py-6 text-center text-space-gray-400">
        <p>&copy; 2024 Red Legion. Web interface for Discord bot payroll system.</p>
      </div>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import LoginPage from './components/LoginPage.vue'
import PayrollWizard from './components/PayrollWizard.vue'

export default {
  name: 'App',
  components: {
    LoginPage,
    PayrollWizard
  },
  setup() {
    const user = ref(null)

    const handleLogin = (userData) => {
      user.value = userData
      localStorage.setItem('red_legion_user', JSON.stringify(userData))
    }

    const logout = () => {
      user.value = null
      localStorage.removeItem('red_legion_user')
    }

    onMounted(() => {
      // Check URL params for OAuth callback
      const urlParams = new URLSearchParams(window.location.search)
      const username = urlParams.get('user')
      const id = urlParams.get('id')
      
      if (username && id) {
        const userData = { username, id }
        handleLogin(userData)
        // Clean up URL
        window.history.replaceState({}, document.title, '/')
      } else {
        // Check localStorage
        const savedUser = localStorage.getItem('red_legion_user')
        if (savedUser) {
          user.value = JSON.parse(savedUser)
        }
      }
    })

    return {
      user,
      handleLogin,
      logout
    }
  }
}
</script>

<style>
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  margin: 0;
  padding: 0;
}

.font-mono {
  font-family: 'JetBrains Mono', monospace;
}
</style>
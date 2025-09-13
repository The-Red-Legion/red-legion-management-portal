<template>
  <div id="app" class="min-h-screen bg-space-gray-900 text-white">
    <!-- Header -->
    <header class="bg-space-gray-800 shadow-lg">
      <div class="max-w-7xl mx-auto px-4 py-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <img src="/red-legion-logo.png" alt="Red Legion" class="h-12 w-12" />
            <h1 class="text-2xl font-bold text-red-legion-500">Red Legion Payroll</h1>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-space-gray-300">Welcome, {{ user.username }}</span>
            <router-link 
              to="/events" 
              class="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
              </svg>
              <span>Events</span>
            </router-link>
            <router-link 
              to="/management" 
              class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
              </svg>
              <span>Management</span>
            </router-link>
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
    <router-view :user="user" @login="handleLogin" />



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
import { apiService } from './api.js'

export default {
  name: 'App',
  setup() {
    // Mock user for development (OAuth disabled)
    const user = ref({ username: "DevUser", id: "123456789", roles: ["admin"] })

    const handleLogin = (userData) => {
      user.value = userData
      localStorage.setItem('red_legion_user', JSON.stringify(userData))
    }

    const logout = () => {
      // Redirect to backend logout endpoint which will clear session and redirect to confirmation page
      window.location.href = apiService.getLogoutUrl()
    }


    onMounted(() => {
      console.log('🚀 App mounted, checking authentication...')
      
      // Check URL params for OAuth callback
      const urlParams = new URLSearchParams(window.location.search)
      const username = urlParams.get('user')
      const id = urlParams.get('id')
      const roles = urlParams.get('roles')
      
      console.log('📋 URL params:', { username, id, roles })
      
      if (username && id) {
        const userData = { username, id, roles: roles ? roles.split('%20') : [] }
        console.log('✅ Found OAuth params, logging in user:', userData)
        handleLogin(userData)
        // Clean up URL
        window.history.replaceState({}, document.title, '/')
      } else {
        // Check localStorage
        const savedUser = localStorage.getItem('red_legion_user')
        console.log('💾 Checking localStorage:', savedUser)
        if (savedUser) {
          user.value = JSON.parse(savedUser)
          console.log('✅ Restored user from localStorage:', user.value)
        }
      }
    })

    return {
      user,
      handleLogin,
      logout,
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
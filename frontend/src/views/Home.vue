<template>
  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 py-8">
    <!-- Auth bypass for testing -->
    <div v-if="!user" class="text-center mb-8">
      <p class="text-white mb-4">Authentication bypass for testing:</p>
      <a 
        href="http://34.28.1.154:8000/auth/login" 
        class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg inline-block"
      >
        Login via Backend (Port 8000)
      </a>
    </div>
    
    <LoginPage v-if="!user" @login="handleLogin" />
    <PayrollWizard v-else :user="user" />
  </main>
</template>

<script>
import { ref, onMounted } from 'vue'
import LoginPage from '../components/LoginPage.vue'
import PayrollWizard from '../components/PayrollWizard.vue'

export default {
  name: 'Home',
  components: {
    LoginPage,
    PayrollWizard
  },
  props: {
    user: {
      type: Object,
      default: null
    }
  },
  setup(props, { emit }) {
    const user = ref(null)
    
    const handleLogin = (userData) => {
      user.value = userData
      localStorage.setItem('red_legion_user', JSON.stringify(userData))
      emit('login', userData)
    }

    onMounted(() => {
      // Check URL params for OAuth callback
      const urlParams = new URLSearchParams(window.location.search)
      const username = urlParams.get('user')
      const id = urlParams.get('id')
      const roles = urlParams.get('roles')
      
      if (username && id) {
        const userData = { username, id, roles: roles ? roles.split('%20') : [] }
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
      handleLogin
    }
  }
}
</script>
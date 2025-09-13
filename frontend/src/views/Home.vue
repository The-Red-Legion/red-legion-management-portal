<template>
  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 py-8">
    <!-- OAuth temporarily disabled for development -->
    <!-- <LoginPage v-if="!user" @login="handleLogin" /> -->
    <PayrollWizard :user="mockUser" />
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
    // Mock user for development (OAuth disabled)
    const mockUser = {
      username: "DevUser",
      id: "123456789",
      roles: ["admin"]
    }
    
    /* OAuth logic temporarily disabled
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
    */

    return {
      mockUser
    }
  }
}
</script>
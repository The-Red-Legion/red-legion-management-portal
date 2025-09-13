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
    const handleLogin = (userData) => {
      emit('login', userData)
    }

    return {
      user: props.user,
      handleLogin
    }
  }
}
</script>
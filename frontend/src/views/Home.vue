<template>
  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 py-8">
    <!-- Debug info -->
    <div class="bg-red-500 text-white p-4 mb-4 rounded">
      DEBUG: User = {{ user ? JSON.stringify(user) : 'null' }}
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
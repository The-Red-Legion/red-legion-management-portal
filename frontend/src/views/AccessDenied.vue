<template>
  <div class="min-h-screen bg-space-gray-900 text-white flex items-center justify-center">
    <div class="max-w-md w-full mx-4">
      <div class="bg-space-gray-800 rounded-lg shadow-lg p-8 text-center">
        <div class="mb-6">
          <svg class="w-16 h-16 mx-auto text-red-legion-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
          </svg>
        </div>
        
        <h1 class="text-3xl font-bold text-red-legion-500 mb-4">Access Denied</h1>
        
        <p class="text-space-gray-300 mb-6">
          You don't have the required permissions to access the Red Legion Payroll system.
        </p>
        
        <div class="bg-space-gray-700 rounded-lg p-4 mb-6">
          <p class="text-sm text-space-gray-400 mb-2">
            <strong>Required roles:</strong>
          </p>
          <ul class="text-sm text-space-gray-300">
            <li>• Admin</li>
            <li>• Org Leaders</li>
          </ul>
        </div>
        
        <p class="text-sm text-space-gray-400 mb-6">
          If you believe you should have access, please contact a Red Legion administrator to verify your Discord roles.
        </p>
        
        <button 
          @click="goHome" 
          class="bg-red-legion-600 hover:bg-red-legion-700 text-white px-6 py-2 rounded-lg transition-colors"
        >
          Return to Login
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AccessDenied',
  methods: {
    goHome() {
      // Clear any stored user data
      localStorage.removeItem('red_legion_user')
      // Redirect to home
      this.$router.push('/')
    }
  }
}
</script>
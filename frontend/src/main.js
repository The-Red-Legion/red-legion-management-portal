import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

// Create and mount the Vue application
const app = createApp(App)

// Use Vue Router
app.use(router)

// Global error handler
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue Error:', err)
  console.error('Component:', vm)
  console.error('Info:', info)
}

// Global warning handler (development only)
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, vm, trace) => {
    console.warn('Vue Warning:', msg)
    console.warn('Trace:', trace)
  }
}

// Mount the app to the DOM
app.mount('#app')
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Management from '../views/Management.vue'
import Events from '../views/Events.vue'
import LogoutConfirmation from '../views/LogoutConfirmation.vue'
import AccessDenied from '../views/AccessDenied.vue'

const routes = [
  {
    path: '/',
    name: 'Management',
    component: Management
  },
  {
    path: '/payroll',
    name: 'Payroll',
    component: Home
  },
  {
    path: '/events',
    name: 'Events',
    component: Events
  },
  {
    path: '/management',
    redirect: '/'
  },
  {
    path: '/logout-confirmation',
    name: 'LogoutConfirmation',
    component: LogoutConfirmation
  },
  {
    path: '/access-denied',
    name: 'AccessDenied',
    component: AccessDenied
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
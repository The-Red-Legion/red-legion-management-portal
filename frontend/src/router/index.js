import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Management from '../views/Management.vue'
import Events from '../views/Events.vue'
import LogoutConfirmation from '../views/LogoutConfirmation.vue'
import AccessDenied from '../views/AccessDenied.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/management',
    name: 'Management',
    component: Management
  },
  {
    path: '/events',
    name: 'Events',
    component: Events
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
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Management from '../views/Management.vue'
import Events from '../views/Events.vue'

const routes = [
  {
    path: '/',
    name: 'Payroll',
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
    path: '/payroll',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory('/mgmt/'),
  routes
})

export default router
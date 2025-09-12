import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Management from '../views/Management.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Management from '../views/Management.vue'
import Events from '../views/Events.vue'

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
    path: '/events/:eventId/monitor',
    name: 'EventMonitor',
    component: () => import('../views/EventMonitor.vue'),
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
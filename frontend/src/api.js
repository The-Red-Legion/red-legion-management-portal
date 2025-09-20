import axios from 'axios'

// Use current domain for API calls in production, localhost for development
const API_BASE_URL = import.meta.env.MODE === 'production'
  ? '/mgmt/api'  // Use /mgmt/api path for production (nginx will proxy to backend)
  : 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Request interceptor for debugging
api.interceptors.request.use(
  config => {
    console.log('API Request:', config.method?.toUpperCase(), config.url, config.data)
    return config
  },
  error => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  response => {
    console.log('API Response:', response.status, response.data)
    return response
  },
  error => {
    console.error('API Response Error:', error.response?.status, error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const apiService = {
  // Events
  async getEvents() {
    const response = await api.get('/events', {
      timeout: 30000  // 30 second timeout for events loading
    })
    return response.data
  },

  async getEventParticipants(eventId) {
    const response = await api.get(`/events/${eventId}/participants`)
    return response.data
  },

  // UEX Prices
  async getUexPrices() {
    const response = await api.get('/uex-prices')
    return response.data
  },

  // Health checks
  async ping() {
    const response = await api.get('/ping')
    return response.data
  },

  async health() {
    const response = await api.get('/health')
    return response.data
  }
}

export default api
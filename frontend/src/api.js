import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

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
  // Authentication
  async loginWithDiscord() {
    const response = await api.get('/auth/login')
    return response.data
  },

  // Events
  async getEvents() {
    const response = await api.get('/events')
    return response.data
  },

  async getEventParticipants(eventId) {
    const response = await api.get(`/events/${eventId}/participants`)
    return response.data
  },

  // Payroll calculation
  async calculatePayroll(eventId, oreQuantities, customPrices = null) {
    const response = await api.post(`/payroll/${eventId}/calculate`, {
      ore_quantities: oreQuantities,
      custom_prices: customPrices
    })
    return response.data
  },

  // UEX Prices (could be expanded later)
  async getUexPrices() {
    // This would call the backend which fetches from UEX API
    // For now, returning default prices from backend
    return {
      'QUANTAINIUM': 21869.0,
      'GOLD': 5832.0,
      'COPPER': 344.0,
      'RICCITE': 20585.0,
      'CORUNDUM': 359.0,
    }
  }
}

export default api
import axios from 'axios'

// Use current domain for API calls in production, localhost for development
const API_BASE_URL = import.meta.env.MODE === 'production' 
  ? '/api'  // Use relative path for production (nginx will proxy to backend)
  : 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true, // Include cookies in requests
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

  async getCurrentUser() {
    const response = await api.get('/auth/user')
    return response.data
  },

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

  // Payroll calculation
  async calculatePayroll(eventId, oreQuantities, customPrices = null, donatingUsers = []) {
    const response = await api.post(`/payroll/${eventId}/calculate`, {
      ore_quantities: oreQuantities,
      custom_prices: customPrices,
      donating_users: donatingUsers
    })
    return response.data
  },

  // UEX Prices
  async getUexPrices() {
    const response = await api.get('/uex-prices')
    return response.data
  },

  // Event Management
  async closeEvent(eventId) {
    const response = await api.post(`/events/${eventId}/close`)
    return response.data
  },

  // Payroll Management
  async finalizePayroll(eventId, oreQuantities, customPrices = null, donatingUsers = []) {
    const response = await api.post(`/payroll/${eventId}/finalize`, {
      ore_quantities: oreQuantities,
      custom_prices: customPrices,
      donating_users: donatingUsers
    })
    return response.data
  },

  // Trading Locations
  async getTradingLocations() {
    const response = await api.get('/trading-locations')
    return response.data
  },

  // Material Pricing
  async getMaterialPrices(materialNames, locationId = null) {
    const materialsParam = Array.isArray(materialNames) ? materialNames.join(',') : materialNames
    const url = locationId 
      ? `/location-prices/${locationId}?materials=${encodeURIComponent(materialsParam)}`
      : `/material-prices/${encodeURIComponent(materialsParam)}`
    const response = await api.get(url)
    return response.data
  },

  // Discord Integration
  async getDiscordChannels() {
    const response = await api.get('/discord/channels')
    return response.data
  },

  // Admin Functions
  async getAdminEvents() {
    const response = await api.get('/admin/events')
    return response.data
  },

  async deleteAdminEvent(eventId) {
    const response = await api.delete(`/admin/events/${eventId}`)
    return response.data
  },

  async createTestEvent(eventType) {
    const response = await api.post(`/admin/create-test-event/${eventType}`)
    return response.data
  },

  async getPayrollSummary(eventId) {
    const response = await api.get(`/admin/payroll-summary/${eventId}`)
    return response.data
  },

  async exportPayroll(eventId) {
    const response = await api.get(`/admin/payroll-export/${eventId}`)
    return response.data
  },

  async refreshUexCache() {
    const response = await api.post('/admin/refresh-uex-cache')
    return response.data
  },

  async createEvent(eventData) {
    const response = await api.post('/events/create', eventData)
    return response.data
  },

  // Auth redirects - return proper URLs for window.location
  getLoginUrl() {
    // Auth endpoints are directly routed, not through /api prefix
    return import.meta.env.MODE === 'production' ? '/auth/login' : 'http://localhost:8000/auth/login'
  },

  getLogoutUrl() {
    // Auth endpoints are directly routed, not through /api prefix
    return import.meta.env.MODE === 'production' ? '/auth/logout' : 'http://localhost:8000/auth/logout'
  },

}

export default api
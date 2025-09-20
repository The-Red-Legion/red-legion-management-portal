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

  // Payroll calculation
  async calculatePayroll(eventId, oreQuantities, customPrices = null, donatingUsers = []) {
    const response = await api.post(`/payroll/${eventId}/calculate`, {
      ore_quantities: oreQuantities,
      custom_prices: customPrices,
      donating_users: donatingUsers
    })
    return response.data
  },

  // Payroll finalization
  async finalizePayroll(eventId, oreQuantities, customPrices = null, donatingUsers = []) {
    const response = await api.post(`/payroll/${eventId}/finalize`, {
      ore_quantities: oreQuantities,
      custom_prices: customPrices,
      donating_users: donatingUsers
    })
    return response.data
  },

  // Payroll export
  async exportPayroll(eventId) {
    const response = await api.get(`/payroll/${eventId}/export`)
    return response.data
  },

  // Event management
  async closeEvent(eventId) {
    const response = await api.post(`/events/${eventId}/close`)
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
  },

  // Discord Integration
  async getDiscordChannels() {
    try {
      const response = await api.get('/discord/channels')
      return response.data
    } catch (error) {
      console.error('Error fetching Discord channels:', error)
      // Return empty channels if API fails - no point in fake channels if Discord isn't connected
      return {
        channels: [],
        message: 'Discord channels unavailable - bot not connected'
      }
    }
  },

  async syncDiscordChannels() {
    try {
      const response = await api.post('/discord/channels/sync')
      return response.data
    } catch (error) {
      console.error('Error syncing Discord channels:', error)
      throw error
    }
  },

  // Admin functions (placeholders for no-auth version)
  async deleteAdminEvent(eventId) {
    throw new Error('Admin functions not available in no-auth mode')
  },

  async createTestEvent(eventType) {
    throw new Error('Admin functions not available in no-auth mode')
  },

  async getPayrollSummary(eventId) {
    const response = await api.get(`/payroll/${eventId}/summary`)
    return response.data
  },

  async exportPayrollAdmin(eventId) {
    throw new Error('Admin functions not available in no-auth mode')
  }
}

export default api
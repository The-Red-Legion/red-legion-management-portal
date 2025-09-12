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
    const response = await api.get('/api/trading-locations')
    return response.data
  },

  // Material Pricing
  async getMaterialPrices(materialNames, locationId = null) {
    const materialsParam = Array.isArray(materialNames) ? materialNames.join(',') : materialNames
    const url = locationId 
      ? `/api/location-prices/${locationId}?materials=${encodeURIComponent(materialsParam)}`
      : `/api/material-prices/${encodeURIComponent(materialsParam)}`
    const response = await api.get(url)
    return response.data
  },

  // PDF Export for calculated payrolls
  async exportCalculatedPayrollPdf(eventId, oreQuantities, customPrices = null, donatingUsers = []) {
    const response = await api.post(`/payroll/${eventId}/export-pdf`, {
      ore_quantities: oreQuantities,
      custom_prices: customPrices,
      donating_users: donatingUsers
    }, {
      responseType: 'blob'  // Important for PDF download
    })
    return response.data
  }
}

export default api
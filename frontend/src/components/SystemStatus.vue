<template>
  <div class="bg-gray-800 p-4 rounded-lg border border-gray-700">
    <h3 class="text-lg font-semibold text-white mb-3 flex items-center">
      <span class="mr-2">🔧</span>
      System Status
    </h3>

    <div v-if="loading" class="text-gray-400">
      Loading system status...
    </div>

    <div v-else-if="error" class="text-red-400">
      Failed to load system status: {{ error }}
    </div>

    <div v-else class="space-y-3">
      <!-- Overall Status -->
      <div class="flex items-center justify-between p-2 rounded bg-gray-700">
        <span class="text-white font-medium">Overall Status</span>
        <span :class="getStatusClass(status.overall_status)">
          {{ getStatusText(status.overall_status) }}
          {{ getStatusIcon(status.overall_status) }}
        </span>
      </div>

      <!-- Individual Services -->
      <div class="space-y-2">
        <div v-for="(service, name) in status.services" :key="name"
             class="flex items-center justify-between p-2 rounded bg-gray-700">
          <div class="flex flex-col">
            <span class="text-white text-sm font-medium">{{ formatServiceName(name) }}</span>
            <span class="text-gray-400 text-xs">{{ service.message }}</span>
            <span v-if="service.source" class="text-gray-500 text-xs">
              Source: {{ service.source }}
            </span>
          </div>
          <span :class="getStatusClass(service.status)">
            {{ getStatusIcon(service.status) }}
          </span>
        </div>
      </div>

      <!-- Last Updated -->
      <div class="text-gray-500 text-xs text-center pt-2 border-t border-gray-600">
        Last updated: {{ formatTimestamp(status.timestamp) }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { apiService } from '../api.js'

export default {
  name: 'SystemStatus',
  setup() {
    const status = ref(null)
    const loading = ref(true)
    const error = ref(null)
    let interval = null

    const fetchStatus = async () => {
      try {
        const response = await fetch('/mgmt/api/status')
        if (response.ok) {
          status.value = await response.json()
          error.value = null
        } else {
          error.value = `HTTP ${response.status}`
        }
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }

    const getStatusClass = (statusValue) => {
      switch (statusValue) {
        case 'connected':
        case 'healthy':
          return 'text-green-400'
        case 'disconnected':
        case 'degraded':
          return 'text-yellow-400'
        case 'error':
        case 'unhealthy':
          return 'text-red-400'
        default:
          return 'text-gray-400'
      }
    }

    const getStatusIcon = (statusValue) => {
      switch (statusValue) {
        case 'connected':
        case 'healthy':
          return '🟢'
        case 'disconnected':
        case 'degraded':
          return '🟡'
        case 'error':
        case 'unhealthy':
          return '🔴'
        default:
          return '⚪'
      }
    }

    const getStatusText = (statusValue) => {
      return statusValue.charAt(0).toUpperCase() + statusValue.slice(1)
    }

    const formatServiceName = (name) => {
      const names = {
        'database': 'Database',
        'uex_prices': 'UEX Prices',
        'discord_bot': 'Discord Bot'
      }
      return names[name] || name
    }

    const formatTimestamp = (timestamp) => {
      return new Date(timestamp).toLocaleString()
    }

    onMounted(() => {
      fetchStatus()
      // Refresh every 30 seconds
      interval = setInterval(fetchStatus, 30000)
    })

    onUnmounted(() => {
      if (interval) {
        clearInterval(interval)
      }
    })

    return {
      status,
      loading,
      error,
      getStatusClass,
      getStatusIcon,
      getStatusText,
      formatServiceName,
      formatTimestamp
    }
  }
}
</script>
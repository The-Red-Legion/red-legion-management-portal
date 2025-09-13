<template>
  <div class="event-monitor">
    <!-- Header -->
    <div class="monitor-header">
      <div class="header-left">
        <button @click="$router.go(-1)" class="back-btn">
          ← Back to Events
        </button>
        <h1>🔴 Live Event Monitor</h1>
      </div>
      <div class="header-right">
        <div class="status-indicator" :class="{ 'live': isLive, 'offline': !isLive }">
          <span class="status-dot"></span>
          {{ isLive ? 'LIVE' : 'OFFLINE' }}
        </div>
        <button @click="refreshData" class="refresh-btn" :disabled="autoRefresh">
          🔄 {{ autoRefresh ? 'Auto-Refresh ON' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading event data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <h3>❌ Error Loading Event</h3>
      <p>{{ error }}</p>
      <button @click="refreshData" class="retry-btn">Try Again</button>
    </div>

    <!-- Event Data -->
    <div v-else-if="eventData" class="monitor-content">
      
      <!-- Event Info Banner -->
      <div class="event-info-banner">
        <div class="event-title">
          <h2>{{ eventData.event_name }}</h2>
          <span class="event-type-badge">{{ eventData.event_type }}</span>
        </div>
        <div class="event-stats">
          <div class="stat">
            <span class="stat-label">Duration</span>
            <span class="stat-value">{{ formatDuration(eventData.event_duration_minutes) }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">Status</span>
            <span class="stat-value">{{ eventData.event_status }}</span>
          </div>
        </div>
      </div>

      <!-- Key Metrics Cards -->
      <div class="metrics-grid">
        <div class="metric-card primary">
          <div class="metric-icon">👥</div>
          <div class="metric-content">
            <h3>Current Participants</h3>
            <div class="metric-value">{{ eventData.current_participants }}</div>
            <div class="metric-subtitle">Active now</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon">🔢</div>
          <div class="metric-content">
            <h3>Total Unique</h3>
            <div class="metric-value">{{ eventData.total_unique_participants }}</div>
            <div class="metric-subtitle">All participants</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon">📊</div>
          <div class="metric-content">
            <h3>Peak Count</h3>
            <div class="metric-value">{{ peakParticipants }}</div>
            <div class="metric-subtitle">Highest active</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon">⏱️</div>
          <div class="metric-content">
            <h3>Avg. Session</h3>
            <div class="metric-value">{{ averageSessionTime }}m</div>
            <div class="metric-subtitle">Per participant</div>
          </div>
        </div>
      </div>

      <!-- Channel Breakdown -->
      <div class="section-card">
        <h3>📻 Channel Breakdown</h3>
        <div v-if="Object.keys(eventData.channel_breakdown).length === 0" class="empty-channels">
          <p>No active participants in channels</p>
        </div>
        <div v-else class="channel-list">
          <div 
            v-for="(count, channelName) in eventData.channel_breakdown" 
            :key="channelName" 
            class="channel-item"
          >
            <div class="channel-name">{{ channelName || 'Unknown Channel' }}</div>
            <div class="channel-count">{{ count }} participants</div>
            <div class="channel-bar">
              <div 
                class="channel-fill" 
                :style="{ width: getChannelPercentage(count) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Participant History Chart -->
      <div class="section-card">
        <div class="chart-header">
          <h3>📈 Participant History</h3>
          <div class="chart-controls">
            <button 
              v-for="period in chartPeriods" 
              :key="period.value"
              @click="chartHours = period.value"
              :class="{ active: chartHours === period.value }"
              class="period-btn"
            >
              {{ period.label }}
            </button>
          </div>
        </div>
        
        <div v-if="participantHistory.length === 0" class="empty-chart">
          <p>No historical data available</p>
        </div>
        <canvas v-else ref="participantChart" class="participant-chart"></canvas>
      </div>

      <!-- Current Participants List -->
      <div class="section-card">
        <h3>👤 Current Participants ({{ eventData.participant_list.length }})</h3>
        
        <div v-if="eventData.participant_list.length === 0" class="empty-participants">
          <p>No participants currently in the event</p>
        </div>
        
        <div v-else class="participants-table-container">
          <table class="participants-table">
            <thead>
              <tr>
                <th>Participant</th>
                <th>Channel</th>
                <th>Duration</th>
                <th>Status</th>
                <th>Last Activity</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="participant in sortedParticipants" 
                :key="participant.user_id"
                :class="{ active: participant.is_active, inactive: !participant.is_active }"
              >
                <td>
                  <div class="participant-info">
                    <span class="participant-name">
                      {{ participant.display_name || participant.username }}
                    </span>
                    <span v-if="participant.display_name" class="participant-username">
                      ({{ participant.username }})
                    </span>
                  </div>
                </td>
                <td>
                  <span class="channel-name">{{ participant.channel_name || 'Unknown' }}</span>
                </td>
                <td>
                  <span class="duration">{{ participant.duration_minutes }}m</span>
                </td>
                <td>
                  <span class="status-badge" :class="{ active: participant.is_active }">
                    {{ participant.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td>
                  <span class="last-activity">
                    {{ formatLastActivity(participant.last_activity) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api.js'

export default {
  name: 'EventMonitor',
  props: {
    eventId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const route = useRoute()
    
    // Reactive state
    const loading = ref(true)
    const error = ref(null)
    const eventData = ref(null)
    const participantHistory = ref([])
    const autoRefresh = ref(true)
    const chartHours = ref(2)
    const participantChart = ref(null)
    
    let refreshInterval = null
    let chartInstance = null
    
    const chartPeriods = [
      { label: '1H', value: 1 },
      { label: '2H', value: 2 },
      { label: '6H', value: 6 },
      { label: '12H', value: 12 },
      { label: '24H', value: 24 }
    ]

    // Computed properties
    const isLive = computed(() => 
      eventData.value && eventData.value.event_status === 'live'
    )

    const peakParticipants = computed(() => {
      if (!participantHistory.value.length) return eventData.value?.current_participants || 0
      return Math.max(...participantHistory.value.map(h => h.total_participants))
    })

    const averageSessionTime = computed(() => {
      if (!eventData.value?.participant_list.length) return 0
      const total = eventData.value.participant_list.reduce((sum, p) => sum + p.duration_minutes, 0)
      return Math.round(total / eventData.value.participant_list.length)
    })

    const sortedParticipants = computed(() => {
      if (!eventData.value?.participant_list) return []
      return [...eventData.value.participant_list].sort((a, b) => {
        if (a.is_active !== b.is_active) {
          return b.is_active - a.is_active // Active first
        }
        return b.duration_minutes - a.duration_minutes // Then by duration
      })
    })

    // Methods
    const loadEventData = async () => {
      try {
        const [metricsResponse, historyResponse] = await Promise.all([
          api.get(`/events/${props.eventId}/live-metrics`),
          api.get(`/events/${props.eventId}/participant-history?hours=${chartHours.value}`)
        ])
        
        eventData.value = metricsResponse
        participantHistory.value = historyResponse.history || []
        
        error.value = null
        
        // Update chart
        await nextTick()
        updateChart()
        
      } catch (err) {
        console.error('Error loading event data:', err)
        error.value = err.message || 'Failed to load event data'
        eventData.value = null
      }
    }

    const refreshData = async () => {
      if (!loading.value) {
        await loadEventData()
      }
    }

    const updateChart = () => {
      if (!participantChart.value || !participantHistory.value.length) return

      // Destroy existing chart
      if (chartInstance) {
        chartInstance.destroy()
      }

      const ctx = participantChart.value.getContext('2d')
      
      // Simple canvas-based chart since we don't want to add Chart.js dependency
      // We'll draw a simple line chart
      drawParticipantChart(ctx)
    }

    const drawParticipantChart = (ctx) => {
      const canvas = participantChart.value
      const width = canvas.width = canvas.offsetWidth * 2 // High DPI
      const height = canvas.height = canvas.offsetHeight * 2
      ctx.scale(2, 2) // Scale back down for crisp lines
      
      const padding = 40
      const chartWidth = width / 2 - padding * 2
      const chartHeight = height / 2 - padding * 2
      
      // Clear canvas
      ctx.clearRect(0, 0, width / 2, height / 2)
      
      if (participantHistory.value.length === 0) return
      
      // Find data bounds
      const maxParticipants = Math.max(...participantHistory.value.map(h => h.total_participants), 1)
      const minTime = new Date(participantHistory.value[0].timestamp).getTime()
      const maxTime = new Date(participantHistory.value[participantHistory.value.length - 1].timestamp).getTime()
      
      // Draw background
      ctx.fillStyle = '#f8f9fa'
      ctx.fillRect(padding, padding, chartWidth, chartHeight)
      
      // Draw grid lines
      ctx.strokeStyle = '#e9ecef'
      ctx.lineWidth = 1
      
      // Horizontal grid lines
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i
        ctx.beginPath()
        ctx.moveTo(padding, y)
        ctx.lineTo(padding + chartWidth, y)
        ctx.stroke()
      }
      
      // Vertical grid lines
      for (let i = 0; i <= 6; i++) {
        const x = padding + (chartWidth / 6) * i
        ctx.beginPath()
        ctx.moveTo(x, padding)
        ctx.lineTo(x, padding + chartHeight)
        ctx.stroke()
      }
      
      // Draw data lines
      ctx.strokeStyle = '#4CAF50'
      ctx.lineWidth = 2
      
      // Total participants line
      ctx.beginPath()
      participantHistory.value.forEach((point, index) => {
        const x = padding + (chartWidth * index) / (participantHistory.value.length - 1)
        const y = padding + chartHeight - (chartHeight * point.total_participants) / maxParticipants
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
      
      // Active participants line
      ctx.strokeStyle = '#2196F3'
      ctx.beginPath()
      participantHistory.value.forEach((point, index) => {
        const x = padding + (chartWidth * index) / (participantHistory.value.length - 1)
        const y = padding + chartHeight - (chartHeight * point.active_participants) / maxParticipants
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
      
      // Draw labels
      ctx.fillStyle = '#333'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(`Max: ${maxParticipants}`, padding, padding - 5)
      ctx.fillText('0', padding, padding + chartHeight + 15)
      
      // Legend
      ctx.fillStyle = '#4CAF50'
      ctx.fillRect(padding + chartWidth - 150, padding + 10, 15, 3)
      ctx.fillStyle = '#333'
      ctx.fillText('Total Participants', padding + chartWidth - 130, padding + 15)
      
      ctx.fillStyle = '#2196F3'
      ctx.fillRect(padding + chartWidth - 150, padding + 30, 15, 3)
      ctx.fillStyle = '#333'
      ctx.fillText('Active Participants', padding + chartWidth - 130, padding + 35)
    }

    const getChannelPercentage = (count) => {
      if (!eventData.value?.current_participants) return 0
      return (count / eventData.value.current_participants) * 100
    }

    const formatDuration = (minutes) => {
      if (!minutes) return '0m'
      if (minutes < 60) return `${minutes}m`
      const hours = Math.floor(minutes / 60)
      const mins = minutes % 60
      return `${hours}h ${mins}m`
    }

    const formatLastActivity = (timestamp) => {
      if (!timestamp) return 'Unknown'
      const now = new Date()
      const activity = new Date(timestamp)
      const diffMinutes = Math.floor((now - activity) / (1000 * 60))
      
      if (diffMinutes < 1) return 'Now'
      if (diffMinutes < 60) return `${diffMinutes}m ago`
      const hours = Math.floor(diffMinutes / 60)
      return `${hours}h ago`
    }

    const startAutoRefresh = () => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
      
      refreshInterval = setInterval(async () => {
        if (autoRefresh.value && !loading.value) {
          await loadEventData()
        }
      }, 10000) // Refresh every 10 seconds
    }

    const stopAutoRefresh = () => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
        refreshInterval = null
      }
    }

    // Watch for chart period changes
    const updateChartPeriod = async () => {
      try {
        const historyResponse = await api.get(`/events/${props.eventId}/participant-history?hours=${chartHours.value}`)
        participantHistory.value = historyResponse.history || []
        await nextTick()
        updateChart()
      } catch (err) {
        console.error('Error updating chart period:', err)
      }
    }

    // Lifecycle
    onMounted(async () => {
      loading.value = true
      await loadEventData()
      loading.value = false
      startAutoRefresh()
    })

    onUnmounted(() => {
      stopAutoRefresh()
      if (chartInstance) {
        chartInstance.destroy()
      }
    })

    return {
      loading,
      error,
      eventData,
      participantHistory,
      autoRefresh,
      chartHours,
      participantChart,
      chartPeriods,
      isLive,
      peakParticipants,
      averageSessionTime,
      sortedParticipants,
      refreshData,
      getChannelPercentage,
      formatDuration,
      formatLastActivity,
      updateChartPeriod
    }
  },
  watch: {
    chartHours() {
      this.updateChartPeriod()
    }
  }
}
</script>

<style scoped>
.event-monitor {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
  background: #f5f5f5;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  padding: 10px 20px;
  border: none;
  background: #6c757d;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.back-btn:hover {
  background: #5a6268;
}

.monitor-header h1 {
  margin: 0;
  font-size: 2em;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 0.9em;
}

.status-indicator.live {
  background: #d4edda;
  color: #155724;
}

.status-indicator.offline {
  background: #f8d7da;
  color: #721c24;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.refresh-btn {
  padding: 10px 20px;
  border: none;
  background: #007bff;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.refresh-btn:hover:not(:disabled) {
  background: #0056b3;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading, .error-state {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.retry-btn {
  margin-top: 20px;
  padding: 12px 24px;
  border: none;
  background: #007bff;
  color: white;
  border-radius: 6px;
  cursor: pointer;
}

.monitor-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.event-info-banner {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.event-title h2 {
  margin: 0 0 10px 0;
  font-size: 1.8em;
  color: #333;
}

.event-type-badge {
  background: #007bff;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: bold;
  text-transform: uppercase;
}

.event-stats {
  display: flex;
  gap: 30px;
}

.stat {
  text-align: center;
}

.stat-label {
  display: block;
  color: #666;
  font-size: 0.9em;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 1.5em;
  font-weight: bold;
  color: #333;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.metric-card {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  gap: 20px;
  transition: transform 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
}

.metric-card.primary {
  border-left: 5px solid #007bff;
}

.metric-icon {
  font-size: 2.5em;
}

.metric-content h3 {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 1em;
  font-weight: normal;
}

.metric-value {
  font-size: 2.5em;
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.metric-subtitle {
  color: #999;
  font-size: 0.9em;
}

.section-card {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.section-card h3 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 1.4em;
}

.channel-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.channel-item {
  display: flex;
  align-items: center;
  gap: 15px;
}

.channel-name {
  font-weight: bold;
  min-width: 150px;
}

.channel-count {
  color: #666;
  min-width: 100px;
}

.channel-bar {
  flex: 1;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.channel-fill {
  height: 100%;
  background: #007bff;
  transition: width 0.5s ease;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-controls {
  display: flex;
  gap: 10px;
}

.period-btn {
  padding: 6px 12px;
  border: 1px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.period-btn:hover {
  background: #f8f9fa;
}

.period-btn.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.participant-chart {
  width: 100%;
  height: 300px;
  border-radius: 8px;
}

.participants-table-container {
  overflow-x: auto;
}

.participants-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.participants-table th,
.participants-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
}

.participants-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #495057;
}

.participants-table tr.active {
  background: #d4edda;
}

.participants-table tr.inactive {
  background: #f8f9fa;
  opacity: 0.7;
}

.participant-info {
  display: flex;
  flex-direction: column;
}

.participant-name {
  font-weight: bold;
}

.participant-username {
  font-size: 0.8em;
  color: #666;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: bold;
  background: #f8d7da;
  color: #721c24;
}

.status-badge.active {
  background: #d4edda;
  color: #155724;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-channels,
.empty-chart,
.empty-participants {
  text-align: center;
  padding: 40px;
  color: #666;
  background: #f8f9fa;
  border-radius: 8px;
}
</style>
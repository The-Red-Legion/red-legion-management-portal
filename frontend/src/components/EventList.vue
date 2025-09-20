<template>
  <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-xl font-semibold text-white">Select Event</h3>
      <div class="flex space-x-2">
        <button 
          @click="eventTypeFilter = 'all'"
          :class="[
            'px-3 py-1 rounded-lg text-sm transition-colors',
            eventTypeFilter === 'all' 
              ? 'bg-red-legion-600 text-white' 
              : 'bg-space-gray-700 text-space-gray-300 hover:bg-space-gray-600'
          ]"
        >
          All Events
        </button>
        <button 
          @click="eventTypeFilter = 'mining'"
          :class="[
            'px-3 py-1 rounded-lg text-sm transition-colors',
            eventTypeFilter === 'mining' 
              ? 'bg-blue-600 text-white' 
              : 'bg-space-gray-700 text-space-gray-300 hover:bg-space-gray-600'
          ]"
        >
          ⛏️ Mining
        </button>
        <button 
          @click="eventTypeFilter = 'salvage'"
          :class="[
            'px-3 py-1 rounded-lg text-sm transition-colors',
            eventTypeFilter === 'salvage' 
              ? 'bg-orange-600 text-white' 
              : 'bg-space-gray-700 text-space-gray-300 hover:bg-space-gray-600'
          ]"
        >
          🔧 Salvage
        </button>
      </div>
    </div>
    
    <div v-if="loading" class="text-center py-8">
      <div class="inline-block w-8 h-8 border-4 border-red-legion-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-space-gray-400 mt-2">Loading events...</p>
    </div>

    <div v-else-if="error" class="text-center py-8">
      <div class="text-red-500 mb-2">
        <svg class="w-12 h-12 mx-auto mb-2" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
      </div>
      <p class="text-red-400 font-medium">Failed to load events</p>
      <p class="text-space-gray-400 text-sm mt-1">{{ error }}</p>
      <button 
        @click="fetchEvents" 
        class="mt-4 px-4 py-2 bg-red-legion-600 hover:bg-red-legion-700 text-white rounded-lg transition-colors"
      >
        Retry
      </button>
    </div>

    <div v-else-if="events.length === 0" class="text-center py-8">
      <div class="text-space-gray-400 mb-2">
        <svg class="w-12 h-12 mx-auto mb-2" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 11c-.55 0-1-.45-1-1V8c0-.55.45-1 1-1s1 .45 1 1v4c0 .55-.45 1-1 1zm1 4h-2v-2h2v2z"/>
        </svg>
      </div>
      <p class="text-space-gray-400">No mining events found</p>
      <p class="text-space-gray-500 text-sm mt-1">Events will appear here after mining sessions</p>
    </div>

    <div v-else class="space-y-3">
      <div 
        v-for="event in filteredEvents" 
        :key="event.event_id"
        @click="selectEvent(event)"
        :class="[
          'cursor-pointer rounded-lg p-4 transition-colors border-2 border-transparent',
          event.event_type === 'salvage' 
            ? 'bg-orange-900/20 hover:bg-orange-900/30 hover:border-orange-500'
            : 'bg-space-gray-700 hover:bg-space-gray-600 hover:border-red-legion-500'
        ]"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <h4 class="font-semibold text-white">
              <span class="mr-2">{{ event.event_type === 'salvage' ? '🔧' : '⛏️' }}</span>
              {{ event.event_name || event.event_id }}
              <span v-if="!event.ended_at" class="ml-2 px-2 py-1 text-xs bg-green-600 text-white rounded-full">
                🔴 LIVE
              </span>
            </h4>
            <p class="text-space-gray-300 text-sm">Organized by {{ event.organizer_name }}</p>
            <p v-if="formatLocation(event)" class="text-space-gray-400 text-sm">📍 {{ formatLocation(event) }}</p>
            <div class="flex items-center space-x-4 mt-2 text-xs text-space-gray-400">
              <span>{{ formatDate(event.started_at) }}</span>
              <span>{{ formatDuration(event.total_duration_minutes) }}</span>
              <span>{{ event.participant_count }} participants</span>
            </div>
            
            <!-- Live Participant Tracking (only for live events) -->
            <div v-if="!event.ended_at" class="mt-3 bg-space-gray-800 rounded-lg p-3">
              <div class="flex items-center justify-between mb-2">
                <h5 class="text-sm font-medium text-white">🟢 Active Participants</h5>
                <button 
                  @click.stop="fetchParticipants(event.event_id)"
                  class="text-xs text-space-gray-400 hover:text-white transition-colors"
                  :disabled="loadingParticipants.has(event.event_id)"
                >
                  {{ loadingParticipants.has(event.event_id) ? 'Loading...' : '🔄 Refresh' }}
                </button>
              </div>
              
              <!-- Participants List -->
              <div v-if="eventParticipants[event.event_id]" class="space-y-1 max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-space-gray-600 scrollbar-track-space-gray-800">
                <div 
                  v-for="participant in eventParticipants[event.event_id]" 
                  :key="participant.user_id"
                  class="flex justify-between items-center text-xs py-1"
                >
                  <span class="text-space-gray-300 truncate flex-1 mr-2">{{ participant.username }}</span>
                  <span class="text-red-legion-400 font-mono">{{ participant.participation_minutes }}m</span>
                  <span class="text-space-gray-500 ml-1">({{ participant.participation_percentage }}%)</span>
                </div>
                
                <!-- Total participants indicator -->
                <div v-if="eventParticipants[event.event_id].length > 0" class="text-xs text-space-gray-500 text-center pt-2 border-t border-space-gray-700">
                  {{ eventParticipants[event.event_id].length }} total participants
                </div>
              </div>
              
              <!-- Loading State -->
              <div v-else-if="loadingParticipants.has(event.event_id)" class="text-xs text-space-gray-500 text-center py-2">
                Loading participants...
              </div>
              
              <!-- No participants yet -->
              <div v-else class="text-xs text-space-gray-500 text-center py-2">
                No active participants data loaded
              </div>
            </div>
          </div>
          
          <!-- Close Event Button for Live Events -->
          <div class="ml-4 flex flex-col items-end space-y-2">
            <div class="text-red-legion-500 font-mono text-sm">{{ event.event_id }}</div>
            
            <button 
              v-if="!event.ended_at" 
              @click.stop="closeEvent(event)"
              class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded-md transition-colors"
            >
              🏁 Close Event
            </button>
            
            <div class="text-space-gray-500 text-xs mt-1">Click to select</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="events.length > 0" class="mt-6 text-center space-y-2">
      <button 
        @click="fetchEvents" 
        class="text-space-gray-400 hover:text-white text-sm transition-colors"
      >
        🔄 Refresh Events
      </button>
      <div v-if="events.some(event => !event.ended_at)" class="text-xs text-green-400">
        🔴 Auto-refreshing live events every 30 seconds
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiService } from '../api.js'

export default {
  name: 'EventList',
  emits: ['event-selected'],
  setup(props, { emit }) {
    const route = useRoute()
    const events = ref([])
    const loading = ref(false)
    const error = ref(null)
    const eventParticipants = ref({}) // Store participants by event_id
    const loadingParticipants = ref(new Set()) // Track which events are loading participants
    const eventTypeFilter = ref('all')
    let refreshInterval = null

    const fetchEvents = async () => {
      loading.value = true
      error.value = null
      
      try {
        const eventData = await apiService.getEvents()
        events.value = eventData
        
        // Auto-fetch participants for live events
        for (const event of eventData) {
          if (!event.ended_at) { // Live event
            fetchParticipants(event.event_id)
          }
        }

        // Check for route query parameter and auto-select event
        const eventIdFromRoute = route.query.event
        if (eventIdFromRoute) {
          const eventToSelect = eventData.find(event => event.event_id === eventIdFromRoute)
          if (eventToSelect) {
            // Auto-select the event after a short delay to ensure UI is ready
            setTimeout(() => {
              selectEvent(eventToSelect)
            }, 500)
          }
        }
      } catch (err) {
        error.value = err.response?.data?.detail || err.message || 'Failed to load events'
        console.error('Failed to fetch events:', err)
      } finally {
        loading.value = false
      }
    }

    const fetchParticipants = async (eventId) => {
      if (loadingParticipants.value.has(eventId)) return // Already loading
      
      loadingParticipants.value.add(eventId)
      
      try {
        const participants = await apiService.getEventParticipants(eventId)
        eventParticipants.value[eventId] = participants
      } catch (err) {
        console.error(`Failed to fetch participants for event ${eventId}:`, err)
        eventParticipants.value[eventId] = []
      } finally {
        loadingParticipants.value.delete(eventId)
      }
    }

    const selectEvent = (event) => {
      emit('event-selected', event)
    }

    const closeEvent = async (event) => {
      if (confirm(`Are you sure you want to close event ${event.event_id}?\n\nThis will end the mining session and calculate final statistics.`)) {
        try {
          const result = await apiService.closeEvent(event.event_id)
          
          // Update the event in the local list
          const eventIndex = events.value.findIndex(e => e.event_id === event.event_id)
          if (eventIndex !== -1) {
            events.value[eventIndex].ended_at = new Date().toISOString()
            events.value[eventIndex].total_participants = result.total_participants
            events.value[eventIndex].total_duration_minutes = result.total_duration_minutes
          }
          
          alert(`Event ${event.event_id} has been closed successfully!\n\n` +
                `Total Participants: ${result.total_participants}\n` +
                `Total Duration: ${result.total_duration_minutes} minutes`)
        } catch (error) {
          console.error('Failed to close event:', error)
          alert('Failed to close event: ' + (error.response?.data?.detail || error.message))
        }
      }
    }

    const formatDate = (dateString) => {
      if (!dateString) return 'Unknown date'
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const formatDuration = (minutes) => {
      if (!minutes) return '0m'
      const hours = Math.floor(minutes / 60)
      const mins = minutes % 60
      
      if (hours > 0) {
        return `${hours}h ${mins}m`
      }
      return `${mins}m`
    }

    const formatLocation = (event) => {
      const parts = []
      
      if (event.system_location) {
        parts.push(event.system_location)
      }
      
      if (event.planet_moon) {
        parts.push(event.planet_moon)
      }
      
      if (event.location_notes) {
        parts.push(`(${event.location_notes})`)
      }
      
      return parts.length > 0 ? parts.join(' - ') : null
    }

    onMounted(() => {
      fetchEvents()
      
      // Auto-refresh live events every 30 seconds
      refreshInterval = setInterval(() => {
        const hasLiveEvents = events.value.some(event => !event.ended_at)
        if (hasLiveEvents) {
          fetchEvents()
        }
      }, 30000)
    })
    
    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    // Computed property to filter events by type
    const filteredEvents = computed(() => {
      if (eventTypeFilter.value === 'all') {
        return events.value
      }
      return events.value.filter(event => event.event_type === eventTypeFilter.value)
    })

    return {
      events,
      filteredEvents,
      loading,
      error,
      eventParticipants,
      loadingParticipants,
      eventTypeFilter,
      fetchEvents,
      fetchParticipants,
      selectEvent,
      closeEvent,
      formatDate,
      formatDuration,
      formatLocation
    }
  }
}
</script>
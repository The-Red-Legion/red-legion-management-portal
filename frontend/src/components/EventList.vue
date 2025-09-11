<template>
  <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
    <h3 class="text-xl font-semibold text-white mb-4">Select Mining Event</h3>
    
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
        v-for="event in events" 
        :key="event.event_id"
        @click="selectEvent(event)"
        class="cursor-pointer bg-space-gray-700 hover:bg-space-gray-600 rounded-lg p-4 transition-colors border-2 border-transparent hover:border-red-legion-500"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <h4 class="font-semibold text-white">{{ event.event_name || event.event_id }}</h4>
            <p class="text-space-gray-300 text-sm">Organized by {{ event.organizer_name }}</p>
            <div class="flex items-center space-x-4 mt-2 text-xs text-space-gray-400">
              <span>{{ formatDate(event.started_at) }}</span>
              <span>{{ formatDuration(event.total_duration_minutes) }}</span>
              <span>{{ event.participant_count }} participants</span>
            </div>
          </div>
          <div class="ml-4 text-right">
            <div class="text-red-legion-500 font-mono text-sm">{{ event.event_id }}</div>
            <div class="text-space-gray-500 text-xs mt-1">Click to select</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="events.length > 0" class="mt-6 text-center">
      <button 
        @click="fetchEvents" 
        class="text-space-gray-400 hover:text-white text-sm transition-colors"
      >
        🔄 Refresh Events
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { apiService } from '../api.js'

export default {
  name: 'EventList',
  emits: ['event-selected'],
  setup(props, { emit }) {
    const events = ref([])
    const loading = ref(false)
    const error = ref(null)

    const fetchEvents = async () => {
      loading.value = true
      error.value = null
      
      try {
        const eventData = await apiService.getEvents()
        events.value = eventData
      } catch (err) {
        error.value = err.response?.data?.detail || err.message || 'Failed to load events'
        console.error('Failed to fetch events:', err)
      } finally {
        loading.value = false
      }
    }

    const selectEvent = (event) => {
      emit('event-selected', event)
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

    onMounted(() => {
      fetchEvents()
    })

    return {
      events,
      loading,
      error,
      fetchEvents,
      selectEvent,
      formatDate,
      formatDuration
    }
  }
}
</script>
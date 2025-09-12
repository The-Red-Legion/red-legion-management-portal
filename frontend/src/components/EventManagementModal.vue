<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-space-gray-800 rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between p-6 border-b border-space-gray-700">
        <h2 class="text-2xl font-bold text-white">Event Management</h2>
        <button @click="$emit('close')" class="text-space-gray-400 hover:text-white transition-colors">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <div class="p-6">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8">
          <div class="inline-block w-8 h-8 border-4 border-red-legion-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p class="text-space-gray-400">Loading events...</p>
        </div>

        <!-- Always show control buttons when not loading -->
        <div v-else>
          <div class="mb-4 flex justify-between items-center">
            <p class="text-space-gray-300">Total Events: {{ events.length }}</p>
            <div class="flex space-x-3">
              <!-- Test Event Creation Buttons -->
              <button 
                @click="createTestEvent('mining')" 
                :disabled="creatingTestEvent"
                :class="[
                  'px-4 py-2 rounded-lg transition-colors flex items-center space-x-2',
                  creatingTestEvent 
                    ? 'bg-gray-500 text-gray-300 cursor-not-allowed' 
                    : 'bg-green-600 hover:bg-green-700 text-white'
                ]"
              >
                <div class="text-lg">⛏️</div>
                <span>{{ creatingTestEvent ? 'Creating...' : 'Test Mining' }}</span>
              </button>
              <button 
                @click="createTestEvent('salvage')" 
                :disabled="creatingTestEvent"
                :class="[
                  'px-4 py-2 rounded-lg transition-colors flex items-center space-x-2',
                  creatingTestEvent 
                    ? 'bg-gray-500 text-gray-300 cursor-not-allowed' 
                    : 'bg-orange-600 hover:bg-orange-700 text-white'
                ]"
              >
                <div class="text-lg">🔧</div>
                <span>{{ creatingTestEvent ? 'Creating...' : 'Test Salvage' }}</span>
              </button>
              <button 
                @click="refreshEvents" 
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
                <span>Refresh</span>
              </button>
              <button 
                @click="refreshUexCache" 
                :disabled="refreshingUexCache"
                :class="[
                  'px-4 py-2 rounded-lg transition-colors flex items-center space-x-2',
                  refreshingUexCache 
                    ? 'bg-gray-500 text-gray-300 cursor-not-allowed' 
                    : 'bg-purple-600 hover:bg-purple-700 text-white'
                ]"
              >
                <div class="text-lg">💎</div>
                <span>{{ refreshingUexCache ? 'Refreshing...' : 'Refresh Prices' }}</span>
              </button>
            </div>
          </div>

          <!-- Events Table -->
          <div v-if="events.length > 0">

          <div class="bg-space-gray-700 rounded-lg overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-space-gray-600">
                  <tr>
                    <th class="text-left py-3 px-4 text-white font-medium">Event ID</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Type</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Name</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Organizer</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Status</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Started</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Ended</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Participants</th>
                    <th class="text-left py-3 px-4 text-white font-medium">Payroll</th>
                    <th class="text-right py-3 px-4 text-white font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="event in events" 
                    :key="event.event_id"
                    class="border-b border-space-gray-600 hover:bg-space-gray-600"
                  >
                    <td class="py-3 px-4">
                      <code class="text-yellow-400 bg-space-gray-800 px-2 py-1 rounded text-sm">
                        {{ event.event_id }}
                      </code>
                    </td>
                    <td class="py-3 px-4">
                      <span :class="[
                        'px-2 py-1 rounded-full text-xs font-medium',
                        event.event_type === 'mining' ? 'bg-blue-500 text-blue-100' : 'bg-orange-500 text-orange-100'
                      ]">
                        {{ event.event_type === 'mining' ? '⛏️ Mining' : '🔧 Salvage' }}
                      </span>
                    </td>
                    <td class="py-3 px-4 text-white">{{ event.event_name || 'N/A' }}</td>
                    <td class="py-3 px-4 text-space-gray-300">{{ event.organizer_name || 'N/A' }}</td>
                    <td class="py-3 px-4">
                      <span :class="[
                        'px-2 py-1 rounded-full text-xs font-medium',
                        event.status === 'open' ? 'bg-green-500 text-green-100' : 'bg-red-500 text-red-100'
                      ]">
                        {{ event.status === 'open' ? '🟢 Open' : '🔴 Closed' }}
                      </span>
                    </td>
                    <td class="py-3 px-4 text-space-gray-300">
                      {{ formatDateTime(event.started_at) }}
                    </td>
                    <td class="py-3 px-4 text-space-gray-300">
                      {{ event.ended_at ? formatDateTime(event.ended_at) : 'N/A' }}
                    </td>
                    <td class="py-3 px-4 text-center">
                      <span class="text-blue-400 font-mono">
                        {{ event.total_participants || 0 }}
                      </span>
                    </td>
                    <td class="py-3 px-4 text-center">
                      <span v-if="event.payroll_calculated" class="text-green-400">✅</span>
                      <span v-else class="text-space-gray-500">❌</span>
                    </td>
                    <td class="py-3 px-4 text-right">
                      <button
                        @click="deleteEvent(event.event_id)"
                        :disabled="deletingEvents.includes(event.event_id)"
                        :class="[
                          'px-3 py-1 rounded text-sm transition-colors',
                          deletingEvents.includes(event.event_id)
                            ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                            : 'bg-red-600 hover:bg-red-700 text-white'
                        ]"
                      >
                        {{ deletingEvents.includes(event.event_id) ? 'Deleting...' : '🗑️ Delete' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

          <!-- No Events State -->
          <div v-else class="text-center py-8">
            <div class="text-4xl mb-4">📋</div>
            <h3 class="text-xl font-medium text-white mb-2">No Events Found</h3>
            <p class="text-space-gray-400">No events have been created yet.</p>
          </div>
        </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'EventManagementModal',
  emits: ['close'],
  setup() {
    const loading = ref(true)
    const events = ref([])
    const deletingEvents = ref([])
    const creatingTestEvent = ref(false)
    const refreshingUexCache = ref(false)

    const formatDateTime = (dateString) => {
      if (!dateString) return 'N/A'
      try {
        const date = new Date(dateString)
        return date.toLocaleString()
      } catch (error) {
        return 'Invalid Date'
      }
    }

    const loadEvents = async () => {
      loading.value = true
      try {
        // Add cache-busting parameter to ensure fresh data
        const response = await fetch(`http://localhost:8000/admin/events?_t=${Date.now()}`)
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data = await response.json()
        events.value = data
        console.log('Loaded events:', data.length)
      } catch (error) {
        console.error('Failed to load events:', error)
        alert('Failed to load events. Please try again.')
      } finally {
        loading.value = false
      }
    }

    const refreshEvents = () => {
      loadEvents()
    }

    const deleteEvent = async (eventId) => {
      if (!confirm(`Are you sure you want to delete event ${eventId}? This will delete all associated data including participants and payroll information. This action cannot be undone.`)) {
        return
      }

      deletingEvents.value.push(eventId)
      try {
        const response = await fetch(`http://localhost:8000/admin/events/${eventId}`, {
          method: 'DELETE'
        })
        
        if (!response.ok) {
          if (response.status === 404) {
            // Event was already deleted, just remove from local list and refresh
            console.log(`Event ${eventId} was already deleted`)
            events.value = events.value.filter(event => event.event_id !== eventId)
            // Refresh to get current server state
            await loadEvents()
            return
          }
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        // Remove the event from the local list
        events.value = events.value.filter(event => event.event_id !== eventId)
        
        console.log(`Event ${eventId} deleted successfully`)
      } catch (error) {
        console.error('Failed to delete event:', error)
        // If it's a 404, the event was already deleted, so refresh the list
        if (error.message.includes('404')) {
          console.log('Event was already deleted, refreshing list...')
          await loadEvents()
        } else {
          alert('Failed to delete event. Please try again.')
        }
      } finally {
        // Remove from deleting list
        deletingEvents.value = deletingEvents.value.filter(id => id !== eventId)
      }
    }

    const createTestEvent = async (eventType) => {
      if (!['mining', 'salvage'].includes(eventType)) {
        alert('Invalid event type')
        return
      }

      creatingTestEvent.value = true
      try {
        const response = await fetch(`http://localhost:8000/admin/create-test-event/${eventType}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
        }
        
        const result = await response.json()
        console.log(`Test ${eventType} event created:`, result)
        
        // Refresh the events list to show the new test event
        await loadEvents()
        
        // Show success message
        alert(`✅ Test ${eventType} event "${result.event.event_name}" created successfully!\n\nEvent ID: ${result.event.event_id}\nParticipants: ${result.event.total_participants}\nDuration: ${Math.round(result.event.total_duration_minutes / 60)} hours`)
        
      } catch (error) {
        console.error(`Failed to create test ${eventType} event:`, error)
        alert(`Failed to create test ${eventType} event. Please try again.\n\nError: ${error.message}`)
      } finally {
        creatingTestEvent.value = false
      }
    }

    const refreshUexCache = async () => {
      refreshingUexCache.value = true
      try {
        const response = await fetch('http://localhost:8000/admin/refresh-uex-cache', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const result = await response.json()
        
        if (result.success) {
          const totalItems = Object.values(result.results).reduce((total, cat) => total + (cat.item_count || 0), 0)
          alert(`✅ UEX price cache refreshed successfully!\n\n${result.message}\nTotal items refreshed: ${totalItems}\n\nPrice data is now current!`)
        } else {
          throw new Error(result.error || 'Unknown error')
        }
        
      } catch (error) {
        console.error('Failed to refresh UEX cache:', error)
        alert(`Failed to refresh UEX price cache. Please try again.\n\nError: ${error.message}`)
      } finally {
        refreshingUexCache.value = false
      }
    }

    onMounted(() => {
      loadEvents()
    })

    return {
      loading,
      events,
      deletingEvents,
      creatingTestEvent,
      refreshingUexCache,
      formatDateTime,
      refreshEvents,
      deleteEvent,
      createTestEvent,
      refreshUexCache
    }
  }
}
</script>
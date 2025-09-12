<template>
  <div class="events-page">
    <!-- Header -->
    <div class="header-section">
      <h1>🎯 Red Legion Events</h1>
      <p>Schedule, manage, and monitor Red Legion operations</p>
      
      <div class="action-buttons">
        <button @click="showCreateEventModal = true" class="create-btn">
          ➕ Create New Event
        </button>
        <button @click="refreshEvents" class="refresh-btn">
          🔄 Refresh
        </button>
      </div>
    </div>

    <!-- Event Tabs -->
    <div class="event-tabs">
      <button 
        @click="activeTab = 'scheduled'" 
        :class="{ active: activeTab === 'scheduled' }"
        class="tab-btn"
      >
        📅 Scheduled Events ({{ scheduledEvents.length }})
      </button>
      <button 
        @click="activeTab = 'live'" 
        :class="{ active: activeTab === 'live' }"
        class="tab-btn"
      >
        🔴 Live Events ({{ liveEvents.length }})
      </button>
      <button 
        @click="activeTab = 'completed'" 
        :class="{ active: activeTab === 'completed' }"
        class="tab-btn"
      >
        ✅ Recent Events ({{ recentEvents.length }})
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading events...</p>
    </div>

    <!-- Scheduled Events Tab -->
    <div v-if="activeTab === 'scheduled' && !loading" class="events-list">
      <div v-if="scheduledEvents.length === 0" class="empty-state">
        <h3>📅 No Scheduled Events</h3>
        <p>Create your first scheduled event to get started!</p>
      </div>
      <div v-else>
        <div v-for="event in scheduledEvents" :key="event.event_id" class="event-card scheduled">
          <div class="event-header">
            <h3>{{ event.event_name }}</h3>
            <span class="event-type">{{ event.event_type }}</span>
          </div>
          <div class="event-details">
            <p><strong>Organizer:</strong> {{ event.organizer_name }}</p>
            <p><strong>Scheduled:</strong> {{ formatDateTime(event.scheduled_start_time) }}</p>
            <p v-if="event.auto_start_enabled" class="auto-start">🤖 Auto-start enabled</p>
            <p v-if="event.tracked_channels" class="channel-info">
              📻 {{ event.tracked_channels.length }} channels configured
            </p>
          </div>
          <div class="event-actions">
            <button @click="startEvent(event.event_id)" class="start-btn">
              ▶️ Start Now
            </button>
            <button @click="editEvent(event)" class="edit-btn">
              ✏️ Edit
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Live Events Tab -->
    <div v-if="activeTab === 'live' && !loading" class="events-list">
      <div v-if="liveEvents.length === 0" class="empty-state">
        <h3>🔴 No Live Events</h3>
        <p>Start an event or wait for scheduled events to begin!</p>
      </div>
      <div v-else>
        <div v-for="event in liveEvents" :key="event.event_id" class="event-card live">
          <div class="event-header">
            <h3>{{ event.event_name }}</h3>
            <span class="event-type live">{{ event.event_type }} • LIVE</span>
          </div>
          <div class="event-details">
            <p><strong>Organizer:</strong> {{ event.organizer_name }}</p>
            <p><strong>Started:</strong> {{ formatDateTime(event.started_at) }}</p>
            <p><strong>Duration:</strong> {{ formatDuration(event.started_at) }}</p>
          </div>
          <div class="event-actions">
            <router-link :to="`/events/${event.event_id}/monitor`" class="monitor-btn">
              📊 Live Monitor
            </router-link>
            <button @click="stopEvent(event.event_id)" class="stop-btn">
              ⏹️ Stop Event
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Events Tab -->
    <div v-if="activeTab === 'completed' && !loading" class="events-list">
      <div v-if="recentEvents.length === 0" class="empty-state">
        <h3>✅ No Recent Events</h3>
        <p>Completed events will appear here.</p>
      </div>
      <div v-else>
        <div v-for="event in recentEvents" :key="event.event_id" class="event-card completed">
          <div class="event-header">
            <h3>{{ event.event_name }}</h3>
            <span class="event-type">{{ event.event_type }}</span>
          </div>
          <div class="event-details">
            <p><strong>Organizer:</strong> {{ event.organizer_name }}</p>
            <p><strong>Duration:</strong> {{ event.total_duration_minutes }} minutes</p>
            <p><strong>Participants:</strong> {{ event.total_participants }}</p>
          </div>
          <div class="event-actions">
            <router-link :to="`/events/${event.event_id}`" class="details-btn">
              📋 View Details
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Event Modal -->
    <div v-if="showCreateEventModal" class="modal-overlay" @click="showCreateEventModal = false">
      <div class="modal" @click.stop>
        <h2>Create New Event</h2>
        <form @submit.prevent="createEvent">
          <div class="form-group">
            <label>Event Name:</label>
            <input v-model="newEvent.event_name" type="text" required />
          </div>
          <div class="form-group">
            <label>Event Type:</label>
            <select v-model="newEvent.event_type" required>
              <option value="mining">Mining</option>
              <option value="salvage">Salvage</option>
              <option value="combat">Combat</option>
              <option value="social">Social</option>
            </select>
          </div>
          <div class="form-group">
            <label>Organizer Name:</label>
            <input v-model="newEvent.organizer_name" type="text" required />
          </div>
          <div class="form-group">
            <label>Location Notes:</label>
            <input v-model="newEvent.location_notes" type="text" />
          </div>
          <div class="form-group">
            <label>Session Notes:</label>
            <textarea v-model="newEvent.session_notes" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label>
              <input v-model="scheduleEvent" type="checkbox" />
              Schedule for later
            </label>
          </div>
          <div v-if="scheduleEvent" class="form-group">
            <label>Scheduled Start Time:</label>
            <input v-model="newEvent.scheduled_start_time" type="datetime-local" />
          </div>
          <div v-if="scheduleEvent" class="form-group">
            <label>
              <input v-model="newEvent.auto_start_enabled" type="checkbox" />
              Auto-start when scheduled time arrives
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" @click="showCreateEventModal = false" class="cancel-btn">
              Cancel
            </button>
            <button type="submit" class="submit-btn">
              {{ scheduleEvent ? '📅 Schedule Event' : '🚀 Start Event' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import api from '../api.js'

export default {
  name: 'Events',
  setup() {
    // Reactive state
    const activeTab = ref('scheduled')
    const loading = ref(false)
    const showCreateEventModal = ref(false)
    const scheduleEvent = ref(false)
    
    const allEvents = ref([])
    const newEvent = reactive({
      event_name: '',
      event_type: 'mining',
      organizer_name: '',
      location_notes: '',
      session_notes: '',
      scheduled_start_time: '',
      auto_start_enabled: false,
      tracked_channels: [],
      primary_channel_id: null
    })

    // Computed properties
    const scheduledEvents = computed(() => 
      allEvents.value.filter(event => ['planned', 'scheduled'].includes(event.event_status))
    )

    const liveEvents = computed(() => 
      allEvents.value.filter(event => event.event_status === 'live' && event.status === 'open')
    )

    const recentEvents = computed(() => 
      allEvents.value.filter(event => event.status === 'closed').slice(0, 10)
    )

    // Methods
    const loadEvents = async () => {
      loading.value = true
      try {
        // Load all events
        const eventsResponse = await api.get('/events')
        allEvents.value = eventsResponse.events || eventsResponse || []

        // Load scheduled events specifically
        try {
          const scheduledResponse = await api.get('/events/scheduled')
          const scheduledEventsData = scheduledResponse.events || []
          
          // Merge scheduled events with all events (avoid duplicates)
          scheduledEventsData.forEach(scheduled => {
            if (!allEvents.value.find(event => event.event_id === scheduled.event_id)) {
              allEvents.value.push(scheduled)
            }
          })
        } catch (err) {
          console.warn('Could not load scheduled events:', err)
        }

      } catch (error) {
        console.error('Error loading events:', error)
        // Set some mock data for development
        allEvents.value = [
          {
            event_id: 'demo-scheduled',
            event_name: 'Sunday Mining Session',
            event_type: 'mining',
            organizer_name: 'Demo User',
            event_status: 'scheduled',
            scheduled_start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
            auto_start_enabled: true,
            status: 'planned'
          }
        ]
      } finally {
        loading.value = false
      }
    }

    const refreshEvents = () => {
      loadEvents()
    }

    const createEvent = async () => {
      try {
        const eventData = { ...newEvent }
        
        // Convert datetime-local to proper ISO string
        if (scheduleEvent.value && eventData.scheduled_start_time) {
          eventData.scheduled_start_time = new Date(eventData.scheduled_start_time).toISOString()
        } else {
          eventData.scheduled_start_time = null
          eventData.auto_start_enabled = false
        }

        const response = await api.post('/events/create', eventData)
        console.log('Event created:', response)
        
        showCreateEventModal.value = false
        resetNewEventForm()
        await loadEvents()
        
        // Switch to appropriate tab
        if (scheduleEvent.value) {
          activeTab.value = 'scheduled'
        } else {
          activeTab.value = 'live'
        }

      } catch (error) {
        console.error('Error creating event:', error)
        alert('Failed to create event. Please try again.')
      }
    }

    const startEvent = async (eventId) => {
      try {
        // For now, we'll just move the event to live status
        // This could be enhanced to call a specific start endpoint
        console.log('Starting event:', eventId)
        await loadEvents()
      } catch (error) {
        console.error('Error starting event:', error)
        alert('Failed to start event.')
      }
    }

    const stopEvent = async (eventId) => {
      try {
        await api.post(`/events/${eventId}/close`)
        console.log('Event stopped:', eventId)
        await loadEvents()
      } catch (error) {
        console.error('Error stopping event:', error)
        alert('Failed to stop event.')
      }
    }

    const editEvent = (event) => {
      console.log('Edit event:', event)
      // TODO: Implement edit functionality
      alert('Edit functionality coming soon!')
    }

    const resetNewEventForm = () => {
      Object.assign(newEvent, {
        event_name: '',
        event_type: 'mining',
        organizer_name: '',
        location_notes: '',
        session_notes: '',
        scheduled_start_time: '',
        auto_start_enabled: false,
        tracked_channels: [],
        primary_channel_id: null
      })
      scheduleEvent.value = false
    }

    const formatDateTime = (dateString) => {
      if (!dateString) return 'Not set'
      return new Date(dateString).toLocaleString()
    }

    const formatDuration = (startTime) => {
      if (!startTime) return 'Unknown'
      const start = new Date(startTime)
      const now = new Date()
      const diffMinutes = Math.floor((now - start) / (1000 * 60))
      
      if (diffMinutes < 60) {
        return `${diffMinutes}m`
      }
      const hours = Math.floor(diffMinutes / 60)
      const minutes = diffMinutes % 60
      return `${hours}h ${minutes}m`
    }

    // Load events on mount
    onMounted(() => {
      loadEvents()
    })

    return {
      activeTab,
      loading,
      showCreateEventModal,
      scheduleEvent,
      allEvents,
      newEvent,
      scheduledEvents,
      liveEvents,
      recentEvents,
      loadEvents,
      refreshEvents,
      createEvent,
      startEvent,
      stopEvent,
      editEvent,
      resetNewEventForm,
      formatDateTime,
      formatDuration
    }
  }
}
</script>

<style scoped>
.events-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header-section {
  text-align: center;
  margin-bottom: 30px;
}

.header-section h1 {
  font-size: 2.5em;
  color: #333;
  margin-bottom: 10px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 15px;
  justify-content: center;
}

.create-btn, .refresh-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1em;
  cursor: pointer;
  transition: all 0.3s ease;
}

.create-btn {
  background: #4CAF50;
  color: white;
}

.create-btn:hover {
  background: #45a049;
  transform: translateY(-1px);
}

.refresh-btn {
  background: #2196F3;
  color: white;
}

.refresh-btn:hover {
  background: #1976D2;
  transform: translateY(-1px);
}

.event-tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 30px;
  border-bottom: 2px solid #eee;
}

.tab-btn {
  padding: 12px 24px;
  border: none;
  background: none;
  font-size: 1em;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-btn:hover {
  background: #f5f5f5;
}

.tab-btn.active {
  border-bottom-color: #4CAF50;
  color: #4CAF50;
  font-weight: bold;
}

.loading {
  text-align: center;
  padding: 40px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.events-list {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
}

.event-card {
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
}

.event-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.event-card.scheduled {
  border-left: 5px solid #FF9800;
}

.event-card.live {
  border-left: 5px solid #F44336;
  animation: pulse 2s infinite;
}

.event-card.completed {
  border-left: 5px solid #4CAF50;
}

@keyframes pulse {
  0% { border-left-color: #F44336; }
  50% { border-left-color: #FF5722; }
  100% { border-left-color: #F44336; }
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.event-header h3 {
  margin: 0;
  font-size: 1.3em;
}

.event-type {
  background: #e3f2fd;
  color: #1976d2;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8em;
  font-weight: bold;
}

.event-type.live {
  background: #ffebee;
  color: #d32f2f;
}

.event-details {
  margin-bottom: 15px;
}

.event-details p {
  margin: 8px 0;
  color: #666;
}

.auto-start {
  color: #4CAF50 !important;
  font-weight: bold;
}

.channel-info {
  color: #2196F3 !important;
}

.event-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.start-btn, .edit-btn, .stop-btn, .monitor-btn, .details-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 0.9em;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  transition: all 0.3s ease;
}

.start-btn {
  background: #4CAF50;
  color: white;
}

.edit-btn {
  background: #FF9800;
  color: white;
}

.stop-btn {
  background: #F44336;
  color: white;
}

.monitor-btn {
  background: #2196F3;
  color: white;
}

.details-btn {
  background: #9C27B0;
  color: white;
}

.start-btn:hover, .edit-btn:hover, .stop-btn:hover, .monitor-btn:hover, .details-btn:hover {
  transform: translateY(-1px);
  opacity: 0.9;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state h3 {
  margin-bottom: 10px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 30px;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin-top: 0;
  margin-bottom: 20px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1em;
  box-sizing: border-box;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 8px;
}

.modal-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 30px;
}

.cancel-btn, .submit-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
}

.cancel-btn {
  background: #ccc;
  color: #333;
}

.submit-btn {
  background: #4CAF50;
  color: white;
}

.cancel-btn:hover, .submit-btn:hover {
  opacity: 0.9;
}
</style>
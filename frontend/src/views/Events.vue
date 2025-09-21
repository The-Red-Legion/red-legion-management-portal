<template>
  <div class="events-page">
    <!-- Header -->
    <div class="header-section">
      <h1>🎯 Red Legion Events</h1>
      <p>Schedule, manage, and monitor Red Legion operations</p>
      
      <div class="action-buttons">
        <button @click="showCreateForm = !showCreateForm" class="create-btn">
          {{ showCreateForm ? '❌ Cancel' : '➕ Create New Event' }}
        </button>
        <button @click="refreshEvents" class="refresh-btn">
          🔄 Refresh
        </button>
      </div>
    </div>

    <!-- Inline Event Creation Form -->
    <div v-if="showCreateForm" class="create-event-section">
      <div class="create-event-container">
        <!-- Step 1: Event Type Selection -->
        <div v-if="createStep === 1" class="event-type-selection">
          <h3 class="section-title">Choose Event Type</h3>
          
          <div class="event-type-grid">
            <!-- Mining Event -->
            <div 
              @click="selectEventType('mining')"
              :class="[
                'event-type-card',
                selectedEventType === 'mining' ? 'selected mining-selected' : ''
              ]"
            >
              <div class="event-type-header">
                <div class="event-type-emoji">⛏️</div>
                <div class="event-type-info">
                  <h4>Mining Event</h4>
                  <p>Organize mining operations with ore collection tracking</p>
                </div>
              </div>
              <div class="event-type-features">
                • Voice channel participation tracking<br>
                • Ore quantity and pricing calculations<br>
                • Automatic payroll distribution
              </div>
            </div>

            <!-- Salvage Event -->
            <div 
              @click="selectEventType('salvage')"
              :class="[
                'event-type-card',
                selectedEventType === 'salvage' ? 'selected salvage-selected' : ''
              ]"
            >
              <div class="event-type-header">
                <div class="event-type-emoji">🔧</div>
                <div class="event-type-info">
                  <h4>Salvage Event</h4>
                  <p>Organize salvage operations with component tracking</p>
                </div>
              </div>
              <div class="event-type-features">
                • Voice channel participation tracking<br>
                • Salvaged component valuation<br>
                • Automatic payroll distribution
              </div>
            </div>

            <!-- Combat Event -->
            <div 
              @click="selectEventType('combat')"
              :class="[
                'event-type-card',
                selectedEventType === 'combat' ? 'selected combat-selected' : ''
              ]"
            >
              <div class="event-type-header">
                <div class="event-type-emoji">⚔️</div>
                <div class="event-type-info">
                  <h4>Combat Event</h4>
                  <p>Organize ship combat and ground combat operations</p>
                </div>
              </div>
              <div class="event-type-features">
                • Voice channel participation tracking<br>
                • Combat performance metrics<br>
                • Ship and equipment loss tracking<br>
                • Victory/objective completion bonuses
              </div>
            </div>

            <!-- Training Event -->
            <div 
              @click="selectEventType('training')"
              :class="[
                'event-type-card',
                selectedEventType === 'training' ? 'selected training-selected' : ''
              ]"
            >
              <div class="event-type-header">
                <div class="event-type-emoji">🎓</div>
                <div class="event-type-info">
                  <h4>Training Event</h4>
                  <p>Organize pilot training and skill development sessions</p>
                </div>
              </div>
              <div class="event-type-features">
                • Voice channel participation tracking<br>
                • Training curriculum management<br>
                • Skill assessment and progression<br>
                • Instructor certification tracking
              </div>
            </div>

            <!-- Cargo Event -->
            <div 
              @click="selectEventType('cargo')"
              :class="[
                'event-type-card',
                selectedEventType === 'cargo' ? 'selected cargo-selected' : ''
              ]"
            >
              <div class="event-type-header">
                <div class="event-type-emoji">📦</div>
                <div class="event-type-info">
                  <h4>Cargo Event</h4>
                  <p>Organize cargo hauling and trade operations</p>
                </div>
              </div>
              <div class="event-type-features">
                • Voice channel participation tracking<br>
                • Cargo manifest and route tracking<br>
                • Trade profit calculations<br>
                • Security escort coordination
              </div>
            </div>
          </div>

          <div class="form-actions">
            <button 
              @click="showCreateForm = false" 
              class="action-btn cancel-btn"
            >
              Cancel
            </button>
            <button 
              @click="nextStep" 
              :disabled="!selectedEventType"
              :class="[
                'action-btn continue-btn',
                !selectedEventType ? 'disabled' : ''
              ]"
            >
              Continue
            </button>
          </div>
        </div>

        <!-- Step 2: Event Details -->
        <div v-else-if="createStep === 2" class="event-details-form">
          <div class="form-header">
            <button @click="previousStep" class="back-btn">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
              </svg>
            </button>
            <h3 class="section-title">
              {{ selectedEventType === 'mining' ? '⛏️' : '🔧' }} {{ selectedEventType.charAt(0).toUpperCase() + selectedEventType.slice(1) }} Event Details
            </h3>
          </div>

          <form @submit.prevent="createEvent" class="event-form">
            <!-- Event Name -->
            <div class="form-group">
              <label>Event Name *</label>
              <input
                v-model="newEvent.event_name"
                type="text"
                :placeholder="getEventNamePlaceholder()"
                required
              />
            </div>

            <!-- Organizer Name -->
            <div class="form-group">
              <label>Organizer (Discord Display Name) *</label>
              <input
                v-model="newEvent.organizer_name"
                type="text"
                placeholder="Your Discord username"
                required
              />
            </div>

            <!-- Location -->
            <div class="form-group">
              <label>{{ getLocationLabel() }}</label>
              <input
                v-model="newEvent.location_notes"
                type="text"
                :placeholder="getLocationPlaceholder()"
              />
            </div>

            <!-- Session Notes -->
            <div class="form-group">
              <label>Session Notes</label>
              <textarea
                v-model="newEvent.session_notes"
                rows="3"
                :placeholder="getSessionNotesPlaceholder()"
              ></textarea>
            </div>

            <!-- Event Scheduling -->
            <div class="form-group">
              <label>Event Start Time *</label>
              <div class="scheduling-options">
                <label class="radio-option">
                  <input 
                    type="radio" 
                    v-model="schedulingType" 
                    value="immediate" 
                    name="scheduling"
                  />
                  <span>Start Immediately</span>
                </label>
                <label class="radio-option">
                  <input 
                    type="radio" 
                    v-model="schedulingType" 
                    value="scheduled" 
                    name="scheduling"
                  />
                  <span>Schedule for Later</span>
                </label>
              </div>
              
              <div v-if="schedulingType === 'scheduled'" class="scheduled-datetime">
                <div class="datetime-inputs">
                  <div>
                    <label>Date</label>
                    <input 
                      type="date" 
                      v-model="newEvent.scheduled_date"
                      :min="getTodayDate()"
                      required
                    />
                  </div>
                  <div>
                    <label>Time</label>
                    <input 
                      type="time" 
                      v-model="newEvent.scheduled_time"
                      required
                    />
                  </div>
                </div>
                <div class="auto-start-option">
                  <label class="checkbox-label">
                    <input
                      v-model="newEvent.auto_start_enabled"
                      type="checkbox"
                    />
                    <span>Auto-start voice tracking at scheduled time</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- Voice Channel Configuration -->
            <div class="voice-channels-section">
              <h4 class="voice-channels-title">Voice Channel Configuration</h4>
              
              <!-- Primary Channel Selection -->
              <div class="form-group">
                <label>Primary Voice Channel *</label>
                <select v-model="newEvent.primary_channel_id" required>
                  <option value="">Select primary channel...</option>
                  <option v-for="channel in availableChannels" :key="channel.id" :value="channel.id">
                    {{ channel.name }}
                  </option>
                </select>
              </div>

              <!-- Additional Tracked Channels -->
              <div class="form-group">
                <label>Additional Tracked Channels</label>
                <p class="field-description">Select additional channels to track for this event (optional)</p>
                <div class="channel-checkboxes">
                  <label 
                    v-for="channel in availableChannels" 
                    :key="channel.id" 
                    class="channel-checkbox-label"
                    :class="{ disabled: channel.id === newEvent.primary_channel_id }"
                  >
                    <input
                      type="checkbox"
                      :value="channel.id"
                      v-model="selectedAdditionalChannels"
                      :disabled="channel.id === newEvent.primary_channel_id"
                    />
                    <span>{{ channel.name }}</span>
                    <span v-if="channel.id === newEvent.primary_channel_id" class="primary-indicator">(Primary)</span>
                  </label>
                </div>
              </div>

              <!-- Discord Integration -->
              <div class="discord-integration">
                <label class="checkbox-label">
                  <input
                    v-model="startDiscordTracking"
                    type="checkbox"
                  />
                  <div class="checkbox-content">
                    <span class="checkbox-title">Start Discord Voice Tracking</span>
                    <p class="checkbox-description">
                      Send command to Discord bot to start voice channel participation tracking
                    </p>
                  </div>
                </label>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="form-actions">
              <button 
                type="button"
                @click="previousStep" 
                class="action-btn cancel-btn"
              >
                Back
              </button>
              <button 
                type="submit"
                :disabled="isCreating"
                :class="[
                  'action-btn submit-btn',
                  isCreating ? 'disabled' : ''
                ]"
              >
                <svg v-if="isCreating" class="loading-icon" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>{{ isCreating ? 'Creating...' : 'Create Event' }}</span>
              </button>
            </div>
          </form>
        </div>

        <!-- Step 3: Success -->
        <div v-else-if="createStep === 3" class="success-message">
          <div class="success-icon">✅</div>
          <div class="success-content">
            <h3>Event Created Successfully!</h3>
            <p>
              Your {{ selectedEventType }} event <strong>"{{ createdEvent?.event_name }}"</strong> has been created.
            </p>
          </div>

          <div class="event-summary">
            <h4>Event Details:</h4>
            <div class="summary-details">
              <div><strong>Event ID:</strong> {{ createdEvent?.event_id }}</div>
              <div><strong>Type:</strong> {{ selectedEventType.charAt(0).toUpperCase() + selectedEventType.slice(1) }}</div>
              <div><strong>Organizer:</strong> {{ createdEvent?.organizer_name }}</div>
              <div v-if="createdEvent?.location_notes"><strong>Location:</strong> {{ createdEvent.location_notes }}</div>
              <div><strong>Status:</strong> <span class="status-open">Open</span></div>
            </div>
          </div>

          <div class="form-actions">
            <button 
              @click="resetForm" 
              class="action-btn submit-btn"
            >
              Close
            </button>
          </div>
        </div>
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
            <span :class="['event-type', `event-type-${event.event_type}`]">{{ event.event_type }}</span>
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
            <span :class="['event-type', 'live', `event-type-${event.event_type}`]">{{ event.event_type }} • LIVE</span>
          </div>
          <div class="event-details">
            <p><strong>Organizer:</strong> {{ event.organizer_name }}</p>
            <p><strong>Started:</strong> {{ formatDateTime(event.started_at) }}</p>
            <p><strong>Duration:</strong> {{ formatDuration(event.started_at) }}</p>
          </div>
          <div class="event-actions">
            <button @click="openLiveDashboard(event)" class="monitor-btn">
              📊 Live Monitor
            </button>
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
            <span :class="['event-type', `event-type-${event.event_type}`]">{{ event.event_type }}</span>
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

    <!-- Live Dashboard Modal -->
    <div v-if="showLiveDashboard" class="modal-overlay" @click="closeLiveDashboard">
      <div class="modal live-dashboard" @click.stop>
        <div class="modal-header">
          <h2>📊 Live Event Monitor</h2>
          <button @click="closeLiveDashboard" class="close-btn">✕</button>
        </div>
        
        <div class="dashboard-content" v-if="currentEvent">
          <div class="event-info">
            <h3>{{ currentEvent.event_name }}</h3>
            <p class="event-status">{{ currentEvent.event_type.toUpperCase() }} • LIVE • {{ formatDuration(currentEvent.started_at) }}</p>
          </div>
          
          <div class="metrics-grid" v-if="liveMetrics">
            <div class="metric-card">
              <div class="metric-value">{{ liveMetrics.current_participants }}</div>
              <div class="metric-label">Currently Active</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ liveMetrics.total_unique_participants }}</div>
              <div class="metric-label">Total Participants</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ Math.floor(liveMetrics.average_session_duration) }}m</div>
              <div class="metric-label">Avg Session</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ Math.floor(liveMetrics.total_participation_minutes) }}m</div>
              <div class="metric-label">Total Time</div>
            </div>
          </div>
          
          <div class="participants-section" v-if="liveMetrics?.participants?.length">
            <h4>Active Participants</h4>
            <div class="participants-list">
              <div v-for="participant in liveMetrics.participants" 
                   :key="participant.user_id" 
                   class="participant-item">
                <div class="participant-info">
                  <strong>{{ participant.username }}</strong>
                  <span class="participation-time">{{ Math.floor(participant.participation_minutes) }}m</span>
                </div>
                <div class="participant-status" :class="{ active: participant.is_currently_active }">
                  {{ participant.is_currently_active ? '🟢 Active' : '🟡 Inactive' }}
                </div>
              </div>
            </div>
          </div>
          
          <div class="channel-breakdown" v-if="liveMetrics?.channel_breakdown?.length">
            <h4>Channel Activity</h4>
            <div class="channels-list">
              <div v-for="channel in liveMetrics.channel_breakdown" 
                   :key="channel.channel_id" 
                   class="channel-item">
                <div class="channel-name">📻 {{ channel.channel_name }}</div>
                <div class="channel-metrics">
                  <span>{{ channel.active_participants }} active</span>
                  <span>{{ channel.total_participants }} total</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="dashboard-actions">
            <button @click="refreshMetrics" class="refresh-btn" :disabled="refreshing">
              🔄 {{ refreshing ? 'Refreshing...' : 'Refresh' }}
            </button>
            <button @click="stopEvent(currentEvent.event_id)" class="stop-btn">
              ⏹️ Stop Event
            </button>
          </div>
        </div>
        
        <div v-if="!liveMetrics && !metricsError" class="loading-state">
          <p>Loading live metrics...</p>
        </div>
        
        <div v-if="metricsError" class="error-state">
          <p>❌ {{ metricsError }}</p>
          <button @click="refreshMetrics" class="retry-btn">Try Again</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import api, { apiService } from '../api.js'

export default {
  name: 'Events',
  props: {
    user: {
      type: Object,
      default: () => null
    }
  },
  setup(props) {
    // Debug user data
    console.log('Events component - User data:', props.user)
    
    // Reactive state
    const activeTab = ref('scheduled')
    const loading = ref(false)
    const showCreateForm = ref(false)
    const createStep = ref(1)
    const selectedEventType = ref('')
    const startDiscordTracking = ref(true)
    const isCreating = ref(false)
    const createdEvent = ref(null)
    const schedulingType = ref('immediate')
    
    // Live dashboard state
    const showLiveDashboard = ref(false)
    const currentEvent = ref(null)
    const liveMetrics = ref(null)
    const metricsError = ref('')
    const refreshing = ref(false)
    
    const allEvents = ref([])
    // Helper function to get user display name
    const getUserDisplayName = () => {
      if (!props.user) return ''
      
      // Try different possible Discord user properties
      return props.user.display_name || 
             props.user.global_name || 
             props.user.username || 
             props.user.displayName ||
             props.user.name ||
             ''
    }

    // Helper functions for event type specific text
    const getEventNamePlaceholder = () => {
      switch (selectedEventType.value) {
        case 'mining': return 'e.g., Sunday Mining Operation'
        case 'salvage': return 'e.g., Salvage Sweep Alpha'
        case 'combat': return 'e.g., Vanduul Incursion Defense'
        case 'training': return 'e.g., Flight Combat Training'
        case 'cargo': return 'e.g., Trade Route Expedition'
        default: return 'Enter event name...'
      }
    }

    const getLocationLabel = () => {
      switch (selectedEventType.value) {
        case 'mining': return 'Mining Location'
        case 'salvage': return 'Salvage Area'
        case 'combat': return 'Combat Zone'
        case 'training': return 'Training Area'
        case 'cargo': return 'Trade Route'
        default: return 'Location'
      }
    }

    const getLocationPlaceholder = () => {
      switch (selectedEventType.value) {
        case 'mining': return 'e.g., Daymar, Lyria, Aaron Halo'
        case 'salvage': return 'e.g., Crusader, Yela Asteroid Belt'
        case 'combat': return 'e.g., Orison Orbit, Pyro System, Stanton Jumpgate'
        case 'training': return 'e.g., Arena Commander, Crusader Training Grounds'
        case 'cargo': return 'e.g., Stanton → Pyro, Port Olisar → Lorville'
        default: return 'Enter location...'
      }
    }

    const getSessionNotesPlaceholder = () => {
      switch (selectedEventType.value) {
        case 'mining': return 'Optional notes about this mining session...'
        case 'salvage': return 'Optional notes about this salvage operation...'
        case 'combat': return 'Optional notes about this combat operation...'
        case 'training': return 'Optional notes about this training session...'
        case 'cargo': return 'Optional notes about this cargo run...'
        default: return 'Optional session notes...'
      }
    }

    const getTodayDate = () => {
      const today = new Date()
      return today.toISOString().split('T')[0]
    }
    
    const newEvent = reactive({
      event_name: '',
      event_type: 'mining',
      organizer_name: getUserDisplayName(),
      organizer_id: props.user?.id || '',
      location_notes: '',
      session_notes: '',
      guild_id: '814699481912049704',
      primary_channel_id: '',
      tracked_channels: [],
      scheduled_date: getTodayDate(),
      scheduled_time: '',
      auto_start_enabled: true
    })

    // Available Discord voice channels (loaded from API)
    const availableChannels = ref([])

    const selectedAdditionalChannels = ref([])

    // Computed properties
    const scheduledEvents = computed(() =>
      allEvents.value.filter(event => ['planned', 'scheduled'].includes(event.event_status))
    )

    const liveEvents = computed(() =>
      allEvents.value.filter(event =>
        event.event_status === 'live' &&
        (event.status === 'open' || event.status === 'active') &&
        event.ended_at === null
      )
    )

    const recentEvents = computed(() =>
      allEvents.value.filter(event =>
        event.ended_at !== null ||
        event.status === 'closed' ||
        event.status === 'completed'
      ).slice(0, 10)
    )

    // Methods
    const loadEvents = async () => {
      loading.value = true
      try {
        // Load all events
        const eventsResponse = await api.get('/events')
        // Handle both array response and object with events property
        if (Array.isArray(eventsResponse)) {
          allEvents.value = eventsResponse
        } else if (eventsResponse && Array.isArray(eventsResponse.events)) {
          allEvents.value = eventsResponse.events
        } else {
          allEvents.value = []
        }

        // Load scheduled events specifically
        try {
          const scheduledResponse = await api.get('/events/scheduled')
          let scheduledEventsData = []
          
          // Handle both array response and object with events property
          if (Array.isArray(scheduledResponse)) {
            scheduledEventsData = scheduledResponse
          } else if (scheduledResponse && Array.isArray(scheduledResponse.events)) {
            scheduledEventsData = scheduledResponse.events
          }
          
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
            organizer_name: 'Red Legion Admin',
            event_status: 'scheduled',
            scheduled_start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
            auto_start_enabled: true,
            status: 'planned'
          },
          {
            event_id: 'demo-combat-scheduled',
            event_name: 'Vanduul Incursion Defense',
            event_type: 'combat',
            organizer_name: 'Combat Leader',
            event_status: 'scheduled',
            scheduled_start_time: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
            auto_start_enabled: false,
            status: 'planned',
            location_notes: 'Orison Orbit'
          },
          {
            event_id: 'demo-salvage-completed',
            event_name: 'Wreck Salvage Operation',
            event_type: 'salvage',
            organizer_name: 'Salvage Chief',
            event_status: 'completed',
            started_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
            ended_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
            total_duration_minutes: 120,
            total_participants: 6,
            status: 'completed'
          },
          {
            event_id: 'demo-training-scheduled',
            event_name: 'Flight Combat Training',
            event_type: 'training',
            organizer_name: 'Training Officer',
            event_status: 'scheduled',
            scheduled_start_time: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
            auto_start_enabled: true,
            status: 'planned',
            location_notes: 'Arena Commander'
          },
          {
            event_id: 'demo-cargo-live',
            event_name: 'Trade Route Expedition',
            event_type: 'cargo',
            organizer_name: 'Cargo Master',
            event_status: 'active',
            started_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
            status: 'active',
            location_notes: 'Stanton → Pyro System'
          }
        ]
      } finally {
        loading.value = false
      }
    }

    const refreshEvents = () => {
      loadEvents()
    }

    const loadDiscordChannels = async () => {
      try {
        const data = await apiService.getDiscordChannels()
        availableChannels.value = data.channels || []
        
      } catch (error) {
        console.error('Error loading Discord channels:', error)
        // Don't use fallback channels - if Discord isn't connected, voice tracking won't work
        availableChannels.value = []
      }
    }

    const selectEventType = (type) => {
      selectedEventType.value = type
      newEvent.event_type = type
    }

    const nextStep = () => {
      if (createStep.value < 3) {
        createStep.value++
      }
    }

    const previousStep = () => {
      if (createStep.value > 1) {
        createStep.value--
      }
    }

    const createEvent = async () => {
      isCreating.value = true
      
      try {
        // Prepare tracked channels array
        const trackedChannels = []
        
        // Add primary channel
        if (newEvent.primary_channel_id) {
          const primaryChannel = availableChannels.value.find(ch => ch.id === newEvent.primary_channel_id)
          if (primaryChannel) {
            trackedChannels.push({
              id: primaryChannel.id,
              name: primaryChannel.name
            })
          }
        }
        
        // Add additional channels
        selectedAdditionalChannels.value.forEach(channelId => {
          const channel = availableChannels.value.find(ch => ch.id === channelId)
          if (channel && !trackedChannels.find(tc => tc.id === channel.id)) {
            trackedChannels.push({
              id: channel.id,
              name: channel.name
            })
          }
        })

        // Prepare event data with proper scheduling
        let scheduledStartTime = null
        if (schedulingType.value === 'scheduled') {
          const dateTime = new Date(`${newEvent.scheduled_date}T${newEvent.scheduled_time}:00`)
          scheduledStartTime = dateTime.toISOString()
        }

        const eventData = {
          event_name: newEvent.event_name,
          event_type: newEvent.event_type,
          organizer_name: newEvent.organizer_name,
          organizer_id: newEvent.organizer_id,
          location_notes: newEvent.location_notes,
          session_notes: newEvent.session_notes,
          guild_id: newEvent.guild_id,
          primary_channel_id: newEvent.primary_channel_id ? parseInt(newEvent.primary_channel_id) : null,
          tracked_channels: trackedChannels,
          scheduled_start_time: scheduledStartTime,
          auto_start_enabled: schedulingType.value === 'scheduled' ? newEvent.auto_start_enabled : true
        }

        console.log('Creating event with data:', eventData)

        const result = await apiService.createEvent(eventData)
        createdEvent.value = result.event
        
        createStep.value = 3
        
        // Auto-close form after 3 seconds
        setTimeout(() => {
          resetForm()
        }, 3000)
        
        // Refresh events list
        await loadEvents()
        
      } catch (error) {
        console.error('Error creating event:', error)
        alert('Failed to create event. Please try again.')
      } finally {
        isCreating.value = false
      }
    }

    const startEvent = async (eventId) => {
      try {
        console.log('Starting event:', eventId)
        
        const response = await api.post(`/events/${eventId}/start`)
        
        if (response.data.success) {
          console.log('Event started successfully:', response.data)
          
          // Show success message
          alert(`Event "${response.data.event.event_name}" started successfully! Discord voice tracking is now active.`)
          
          // Reload events to reflect new status
          await loadEvents()
        } else {
          throw new Error(response.data.message || 'Failed to start event')
        }
      } catch (error) {
        console.error('Error starting event:', error)
        
        if (error.response?.status === 404) {
          alert('Event not found or not in scheduled status. Only scheduled events can be started manually.')
        } else if (error.response?.data?.detail) {
          alert(`Failed to start event: ${error.response.data.detail}`)
        } else {
          alert('Failed to start event. Please try again.')
        }
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

    // Live dashboard functions
    const openLiveDashboard = async (event) => {
      currentEvent.value = event
      showLiveDashboard.value = true
      metricsError.value = ''
      
      // Load initial metrics
      await loadLiveMetrics(event.event_id)
    }

    const closeLiveDashboard = () => {
      showLiveDashboard.value = false
      currentEvent.value = null
      liveMetrics.value = null
      metricsError.value = ''
    }

    const loadLiveMetrics = async (eventId) => {
      try {
        refreshing.value = true
        metricsError.value = ''
        
        const response = await api.get(`/events/${eventId}/live-metrics`)
        liveMetrics.value = response.data
        
        console.log('Live metrics loaded:', response.data)
      } catch (error) {
        console.error('Error loading live metrics:', error)
        
        if (error.response?.status === 404) {
          metricsError.value = 'Event not found or not live'
        } else if (error.response?.data?.detail) {
          metricsError.value = error.response.data.detail
        } else {
          metricsError.value = 'Failed to load live metrics'
        }
      } finally {
        refreshing.value = false
      }
    }

    const refreshMetrics = async () => {
      if (currentEvent.value) {
        await loadLiveMetrics(currentEvent.value.event_id)
      }
    }

    const resetForm = () => {
      showCreateForm.value = false
      createStep.value = 1
      selectedEventType.value = ''
      startDiscordTracking.value = true
      isCreating.value = false
      createdEvent.value = null
      selectedAdditionalChannels.value = []
      schedulingType.value = 'immediate'
      Object.assign(newEvent, {
        event_name: '',
        event_type: 'mining',
        organizer_name: getUserDisplayName(),
        organizer_id: props.user?.id || '',
        location_notes: '',
        session_notes: '',
        guild_id: '814699481912049704',
        primary_channel_id: '',
        tracked_channels: [],
        scheduled_date: getTodayDate(),
        scheduled_time: '',
        auto_start_enabled: true
      })
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

    // Load events and channels on mount
    onMounted(() => {
      loadEvents()
      loadDiscordChannels()
    })

    return {
      activeTab,
      loading,
      showCreateForm,
      createStep,
      selectedEventType,
      startDiscordTracking,
      isCreating,
      createdEvent,
      allEvents,
      newEvent,
      availableChannels,
      selectedAdditionalChannels,
      scheduledEvents,
      liveEvents,
      recentEvents,
      loadEvents,
      refreshEvents,
      loadDiscordChannels,
      selectEventType,
      nextStep,
      previousStep,
      createEvent,
      resetForm,
      startEvent,
      stopEvent,
      editEvent,
      formatDateTime,
      formatDuration,
      getEventNamePlaceholder,
      getLocationLabel,
      getLocationPlaceholder,
      getSessionNotesPlaceholder,
      schedulingType,
      getTodayDate,
      // Live dashboard
      showLiveDashboard,
      currentEvent,
      liveMetrics,
      metricsError,
      refreshing,
      openLiveDashboard,
      closeLiveDashboard,
      refreshMetrics
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
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8em;
  font-weight: bold;
  text-transform: uppercase;
}

.event-type-mining {
  background: #e3f2fd;
  color: #1976d2;
}

.event-type-salvage {
  background: #fff3cd;
  color: #856404;
}

.event-type-combat {
  background: #f8d7da;
  color: #721c24;
}

.event-type-training {
  background: #e2e3f3;
  color: #6f42c1;
}

.event-type-cargo {
  background: #d1ecf1;
  color: #0c5460;
}

/* Scheduling Options */
.scheduling-options {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.radio-option:hover {
  background-color: #f8f9fa;
}

.radio-option input[type="radio"] {
  width: auto;
  margin: 0;
}

.scheduled-datetime {
  margin-top: 15px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.datetime-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 15px;
}

.datetime-inputs > div {
  display: flex;
  flex-direction: column;
}

.datetime-inputs label {
  margin-bottom: 5px;
  font-size: 0.9em;
  font-weight: 600;
  color: #495057;
}

.datetime-inputs input {
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 0.95em;
  color: #495057;
}

.auto-start-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auto-start-option input[type="checkbox"] {
  width: auto;
  margin: 0;
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
  color: #333;
  background-color: white;
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

/* Inline Event Creation Form Styles */
.create-event-section {
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  margin-bottom: 30px;
  overflow: hidden;
}

.create-event-container {
  padding: 30px;
}

.section-title {
  font-size: 1.5em;
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.form-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 15px;
}

.back-btn {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: #e9ecef;
  color: #333;
}

.back-btn svg {
  width: 20px;
  height: 20px;
}

/* Event Type Selection */
.event-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.event-type-card {
  border: 2px solid #dee2e6;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.event-type-card:hover {
  border-color: #6c757d;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.event-type-card.selected {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.event-type-card.mining-selected {
  border-color: #007bff;
  background: #e3f2fd;
}

.event-type-card.salvage-selected {
  border-color: #fd7e14;
  background: #fff3cd;
}

.event-type-card.combat-selected {
  border-color: #dc3545;
  background: #f8d7da;
}

.event-type-card.training-selected {
  border-color: #6f42c1;
  background: #e2e3f3;
}

.event-type-card.cargo-selected {
  border-color: #20c997;
  background: #d1ecf1;
}

.event-type-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.event-type-emoji {
  font-size: 2em;
}

.event-type-info h4 {
  margin: 0 0 8px 0;
  font-size: 1.2em;
  color: #333;
}

.event-type-info p {
  margin: 0;
  color: #666;
  font-size: 0.9em;
}

.event-type-features {
  color: #666;
  font-size: 0.85em;
  line-height: 1.6;
}

/* Event Form */
.event-form {
  display: grid;
  gap: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 1em;
  box-sizing: border-box;
  transition: border-color 0.3s ease;
  color: #333;
  background-color: white;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #007bff;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

/* Discord Integration */
.discord-integration {
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
  margin-top: 4px;
}

.checkbox-content {
  flex: 1;
}

.checkbox-title {
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 4px;
}

.checkbox-description {
  margin: 0;
  color: #666;
  font-size: 0.9em;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 20px;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1em;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn.cancel-btn {
  background: #6c757d;
  color: white;
}

.action-btn.cancel-btn:hover {
  background: #5a6268;
}

.action-btn.continue-btn {
  background: #28a745;
  color: white;
}

.action-btn.continue-btn:hover:not(.disabled) {
  background: #218838;
}

.action-btn.submit-btn {
  background: #007bff;
  color: white;
}

.action-btn.submit-btn:hover:not(.disabled) {
  background: #0056b3;
}

.action-btn.disabled {
  background: #6c757d;
  color: #adb5bd;
  cursor: not-allowed;
}

.loading-icon {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

/* Success Message */
.success-message {
  text-align: center;
}

.success-icon {
  font-size: 4em;
  margin-bottom: 20px;
}

.success-content h3 {
  color: #28a745;
  margin-bottom: 10px;
}

.success-content p {
  color: #666;
  margin-bottom: 30px;
}

.event-summary {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
  text-align: left;
}

.event-summary h4 {
  margin: 0 0 15px 0;
  color: #333;
}

.summary-details {
  display: grid;
  gap: 8px;
}

.summary-details div {
  color: #666;
}

.summary-details strong {
  color: #333;
}

.status-open {
  color: #28a745;
  font-weight: bold;
}

/* Voice Channel Configuration */
.voice-channels-section {
  background: #f1f3f4;
  border: 2px solid #dee2e6;
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 20px;
}

.voice-channels-title {
  font-size: 1.2em;
  color: #333;
  margin-bottom: 20px;
  font-weight: 600;
  text-align: center;
}

.field-description {
  margin: 8px 0 12px 0;
  color: #666;
  font-size: 0.9em;
  line-height: 1.4;
}

.channel-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 12px;
  padding: 15px;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}

.channel-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.channel-checkbox-label:hover:not(.disabled) {
  background: #f8f9fa;
}

.channel-checkbox-label.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f8f9fa;
}

.channel-checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.primary-indicator {
  color: #007bff;
  font-size: 0.8em;
  font-weight: 600;
}

/* Live Dashboard Styles */
.live-dashboard {
  width: 90vw;
  max-width: 1000px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5em;
  cursor: pointer;
  color: #999;
  padding: 5px;
}

.close-btn:hover {
  color: #666;
}

.dashboard-content {
  padding: 20px;
}

.event-info {
  text-align: center;
  margin-bottom: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
}

.event-info h3 {
  margin: 0 0 10px 0;
  font-size: 1.5em;
}

.event-status {
  margin: 0;
  font-size: 1em;
  opacity: 0.9;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  text-align: center;
  border-left: 4px solid #667eea;
}

.metric-value {
  font-size: 2em;
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.metric-label {
  color: #666;
  font-size: 0.9em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.participants-section,
.channel-breakdown {
  margin-bottom: 30px;
}

.participants-section h4,
.channel-breakdown h4 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 1.2em;
}

.participants-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.participant-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.participant-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.participant-info strong {
  color: #333;
}

.participation-time {
  color: #666;
  font-size: 0.9em;
}

.participant-status {
  font-size: 0.9em;
  padding: 4px 8px;
  border-radius: 20px;
  background: #f8f9fa;
  color: #666;
}

.participant-status.active {
  background: #d4edda;
  color: #155724;
}

.channels-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.channel-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.channel-name {
  font-weight: 600;
  color: #333;
}

.channel-metrics {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: #666;
}

.dashboard-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.refresh-btn,
.retry-btn {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
  transition: background 0.2s;
}

.refresh-btn:hover,
.retry-btn:hover {
  background: #5a6fd8;
}

.refresh-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 40px;
}

.loading-state p {
  color: #666;
  font-size: 1.1em;
}

.error-state p {
  color: #dc3545;
  font-size: 1.1em;
  margin-bottom: 20px;
}

.monitor-btn {
  background: #28a745;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.9em;
  transition: background 0.2s;
  border: none;
  cursor: pointer;
}

.monitor-btn:hover {
  background: #218838;
  color: white;
}
</style>
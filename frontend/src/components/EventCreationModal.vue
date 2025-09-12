<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-space-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between p-6 border-b border-space-gray-700">
        <h2 class="text-2xl font-bold text-white">Create New Event</h2>
        <button @click="$emit('close')" class="text-space-gray-400 hover:text-white transition-colors">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <div class="p-6">
        <!-- Step 1: Event Type Selection -->
        <div v-if="currentStep === 1" class="space-y-6">
          <h3 class="text-xl font-semibold text-white mb-4">Choose Event Type</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Mining Event -->
            <div 
              @click="selectEventType('mining')"
              :class="[
                'p-6 border-2 rounded-lg cursor-pointer transition-all duration-200',
                selectedEventType === 'mining' 
                  ? 'border-blue-500 bg-blue-500/10' 
                  : 'border-space-gray-600 hover:border-blue-400'
              ]"
            >
              <div class="flex items-center space-x-3">
                <div class="text-3xl">⛏️</div>
                <div>
                  <h4 class="text-lg font-semibold text-white">Mining Event</h4>
                  <p class="text-space-gray-300 text-sm">Organize mining operations with ore collection tracking</p>
                </div>
              </div>
              <div class="mt-4 text-sm text-space-gray-400">
                • Voice channel participation tracking<br>
                • Ore quantity and pricing calculations<br>
                • Automatic payroll distribution
              </div>
            </div>

            <!-- Salvage Event -->
            <div 
              @click="selectEventType('salvage')"
              :class="[
                'p-6 border-2 rounded-lg cursor-pointer transition-all duration-200',
                selectedEventType === 'salvage' 
                  ? 'border-orange-500 bg-orange-500/10' 
                  : 'border-space-gray-600 hover:border-orange-400'
              ]"
            >
              <div class="flex items-center space-x-3">
                <div class="text-3xl">🔧</div>
                <div>
                  <h4 class="text-lg font-semibold text-white">Salvage Event</h4>
                  <p class="text-space-gray-300 text-sm">Organize salvage operations with component tracking</p>
                </div>
              </div>
              <div class="mt-4 text-sm text-space-gray-400">
                • Voice channel participation tracking<br>
                • Salvaged component valuation<br>
                • Automatic payroll distribution
              </div>
            </div>
          </div>

          <div class="flex justify-end space-x-3">
            <button 
              @click="$emit('close')" 
              class="px-4 py-2 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button 
              @click="nextStep" 
              :disabled="!selectedEventType"
              :class="[
                'px-4 py-2 rounded-lg transition-colors',
                selectedEventType 
                  ? 'bg-red-legion-600 hover:bg-red-legion-700 text-white' 
                  : 'bg-space-gray-600 text-space-gray-400 cursor-not-allowed'
              ]"
            >
              Continue
            </button>
          </div>
        </div>

        <!-- Step 2: Event Details -->
        <div v-else-if="currentStep === 2" class="space-y-6">
          <div class="flex items-center space-x-3 mb-6">
            <button 
              @click="previousStep" 
              class="text-space-gray-400 hover:text-white transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
              </svg>
            </button>
            <h3 class="text-xl font-semibold text-white">
              {{ selectedEventType === 'mining' ? '⛏️' : '🔧' }} {{ selectedEventType.charAt(0).toUpperCase() + selectedEventType.slice(1) }} Event Details
            </h3>
          </div>

          <form @submit.prevent="createEvent" class="space-y-4">
            <!-- Event Name -->
            <div>
              <label for="eventName" class="block text-sm font-medium text-space-gray-300 mb-2">
                Event Name *
              </label>
              <input
                id="eventName"
                v-model="eventForm.event_name"
                type="text"
                :placeholder="selectedEventType === 'mining' ? 'e.g., Sunday Mining Operation' : 'e.g., Salvage Sweep Alpha'"
                class="w-full px-3 py-2 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white placeholder-space-gray-400 focus:outline-none focus:border-red-legion-500"
                required
              />
            </div>

            <!-- Organizer Name (read-only from Discord user) -->
            <div>
              <label for="organizerName" class="block text-sm font-medium text-space-gray-300 mb-2">
                Organizer (Discord Display Name) *
              </label>
              <div class="w-full px-3 py-2 bg-space-gray-800 border border-space-gray-600 rounded-lg text-space-gray-300">
                {{ eventForm.organizer_name }}
              </div>
            </div>

            <!-- Location -->
            <div>
              <label for="location" class="block text-sm font-medium text-space-gray-300 mb-2">
                {{ selectedEventType === 'mining' ? 'Mining Location' : 'Salvage Area' }}
              </label>
              <input
                id="location"
                v-model="eventForm.location_notes"
                type="text"
                :placeholder="selectedEventType === 'mining' ? 'e.g., Daymar, Lyria, Aaron Halo' : 'e.g., Crusader, Yela Asteroid Belt'"
                class="w-full px-3 py-2 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white placeholder-space-gray-400 focus:outline-none focus:border-red-legion-500"
              />
            </div>

            <!-- Session Notes -->
            <div>
              <label for="sessionNotes" class="block text-sm font-medium text-space-gray-300 mb-2">
                Session Notes
              </label>
              <textarea
                id="sessionNotes"
                v-model="eventForm.session_notes"
                rows="3"
                :placeholder="selectedEventType === 'mining' ? 'Optional notes about this mining session...' : 'Optional notes about this salvage operation...'"
                class="w-full px-3 py-2 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white placeholder-space-gray-400 focus:outline-none focus:border-red-legion-500"
              ></textarea>
            </div>

            <!-- Discord Integration Option -->
            <div class="bg-space-gray-700 rounded-lg p-4">
              <label class="flex items-center space-x-3">
                <input
                  v-model="startDiscordTracking"
                  type="checkbox"
                  class="w-4 h-4 text-red-legion-600 bg-space-gray-600 border-space-gray-500 rounded focus:ring-red-legion-500"
                />
                <div>
                  <span class="text-white font-medium">Start Discord Voice Tracking</span>
                  <p class="text-sm text-space-gray-400">
                    Send command to Discord bot to start voice channel participation tracking
                  </p>
                </div>
              </label>
            </div>

            <!-- Action Buttons -->
            <div class="flex justify-end space-x-3 pt-4">
              <button 
                type="button"
                @click="previousStep" 
                class="px-4 py-2 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors"
              >
                Back
              </button>
              <button 
                type="submit"
                :disabled="isCreating"
                :class="[
                  'px-6 py-2 rounded-lg transition-colors flex items-center space-x-2',
                  isCreating 
                    ? 'bg-space-gray-600 text-space-gray-400 cursor-not-allowed' 
                    : 'bg-red-legion-600 hover:bg-red-legion-700 text-white'
                ]"
              >
                <svg v-if="isCreating" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>{{ isCreating ? 'Creating...' : 'Create Event' }}</span>
              </button>
            </div>
          </form>
        </div>

        <!-- Step 3: Success -->
        <div v-else-if="currentStep === 3" class="text-center space-y-6">
          <div class="text-6xl">✅</div>
          <div>
            <h3 class="text-2xl font-semibold text-white mb-2">Event Created Successfully!</h3>
            <p class="text-space-gray-300">
              Your {{ selectedEventType }} event <strong>"{{ createdEvent?.event_name }}"</strong> has been created.
            </p>
          </div>

          <div class="bg-space-gray-700 rounded-lg p-4">
            <h4 class="font-semibold text-white mb-2">Event Details:</h4>
            <div class="text-left space-y-1 text-sm text-space-gray-300">
              <div><strong>Event ID:</strong> {{ createdEvent?.event_id }}</div>
              <div><strong>Type:</strong> {{ selectedEventType.charAt(0).toUpperCase() + selectedEventType.slice(1) }}</div>
              <div><strong>Organizer:</strong> {{ createdEvent?.organizer_name }}</div>
              <div v-if="createdEvent?.location_notes"><strong>Location:</strong> {{ createdEvent.location_notes }}</div>
              <div><strong>Status:</strong> <span class="text-green-400">Open</span></div>
            </div>
          </div>

          <div v-if="startDiscordTracking && discordIntegrationStatus" :class="[
            'rounded-lg p-4',
            discordIntegrationStatus.success 
              ? 'bg-green-500/10 border border-green-500/30' 
              : 'bg-red-500/10 border border-red-500/30'
          ]">
            <h4 :class="[
              'font-semibold mb-2',
              discordIntegrationStatus.success ? 'text-green-400' : 'text-red-400'
            ]">
              {{ discordIntegrationStatus.success ? '✅' : '❌' }} Discord Integration
            </h4>
            <p class="text-sm text-space-gray-300">
              {{ discordIntegrationStatus.message }}
            </p>
            <div v-if="discordIntegrationStatus.success" class="mt-2 text-xs text-green-300">
              🎤 Voice channel tracking is now active!
            </div>
            <div v-else class="mt-2 text-xs text-red-300">
              💡 You can still manually start tracking with: <code class="bg-space-gray-800 px-1 rounded">/{{ selectedEventType }} start</code>
            </div>
          </div>
          
          <div v-else-if="startDiscordTracking && !discordIntegrationStatus" class="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
            <h4 class="font-semibold text-yellow-400 mb-2">⏳ Discord Integration</h4>
            <p class="text-sm text-space-gray-300">
              Connecting to Discord bot...
            </p>
          </div>

          <div class="flex justify-center space-x-3">
            <button 
              @click="$emit('close')" 
              class="px-6 py-2 bg-red-legion-600 hover:bg-red-legion-700 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'

export default {
  name: 'EventCreationModal',
  props: {
    user: {
      type: Object,
      required: true
    }
  },
  emits: ['close', 'event-created'],
  setup(props, { emit }) {
    const currentStep = ref(1)
    const selectedEventType = ref('')
    const startDiscordTracking = ref(true)
    const isCreating = ref(false)
    const createdEvent = ref(null)
    const discordIntegrationStatus = ref(null)

    const eventForm = ref({
      event_name: '',
      organizer_name: props.user?.global_name || props.user?.username || '',
      organizer_id: props.user?.id || '',
      location_notes: '',
      session_notes: '',
      event_type: 'mining',
      guild_id: '814699481912049704' // Red Legion Discord server ID
    })

    const selectEventType = (type) => {
      selectedEventType.value = type
      eventForm.value.event_type = type
    }

    const nextStep = () => {
      if (currentStep.value < 3) {
        currentStep.value++
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    const createEvent = async () => {
      isCreating.value = true
      
      try {
        const response = await fetch('http://localhost:8000/events/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(eventForm.value)
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result = await response.json()
        createdEvent.value = result.event
        
        // If Discord tracking is enabled, call the Discord bot API
        if (startDiscordTracking.value) {
          try {
            console.log('🤖 Starting Discord voice tracking...')
            const discordResponse = await fetch('http://localhost:8001/events/start', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                event_id: result.event.event_id,
                event_name: result.event.event_name,
                event_type: result.event.event_type,
                organizer_name: result.event.organizer_name,
                organizer_id: result.event.organizer_id || props.user?.id,
                guild_id: result.event.guild_id || '814699481912049704', // Red Legion server ID
                location: result.event.location_notes,
                notes: result.event.session_notes
              })
            })

            if (discordResponse.ok) {
              const discordResult = await discordResponse.json()
              console.log('✅ Discord voice tracking started:', discordResult)
              discordIntegrationStatus.value = {
                success: true,
                message: discordResult.message
              }
            } else {
              const errorText = await discordResponse.text()
              console.error('❌ Discord integration failed:', errorText)
              discordIntegrationStatus.value = {
                success: false,
                message: `Discord bot connection failed: ${errorText}`
              }
            }
          } catch (discordError) {
            console.error('❌ Discord API error:', discordError)
            discordIntegrationStatus.value = {
              success: false,
              message: `Discord bot not available: ${discordError.message}`
            }
          }
        }
        
        currentStep.value = 3
        emit('event-created', result)
        
        // Auto-close modal after 3 seconds on success
        setTimeout(() => {
          emit('close')
        }, 3000)
        
      } catch (error) {
        console.error('Error creating event:', error)
        alert('Failed to create event. Please try again.')
      } finally {
        isCreating.value = false
      }
    }

    return {
      currentStep,
      selectedEventType,
      startDiscordTracking,
      isCreating,
      createdEvent,
      discordIntegrationStatus,
      eventForm,
      selectEventType,
      nextStep,
      previousStep,
      createEvent
    }
  }
}
</script>
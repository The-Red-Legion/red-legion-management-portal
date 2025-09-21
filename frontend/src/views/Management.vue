<template>
  <div class="min-h-screen bg-space-gray-900 py-8">
    <div class="max-w-7xl mx-auto px-4">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-white mb-2">Event Management</h1>
            <p class="text-space-gray-400">Manage all events, participants, and payroll data</p>
          </div>
          <router-link 
            to="/" 
            class="bg-space-gray-700 hover:bg-space-gray-600 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2 text-white"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
            <span>Back to Payroll</span>
          </router-link>
        </div>
      </div>

      <!-- System Status -->
      <div class="mb-6">
        <SystemStatus />
      </div>

      <!-- Main Content -->
      <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8">
          <div class="inline-block w-8 h-8 border-4 border-red-legion-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p class="text-space-gray-400">Loading events...</p>
        </div>

        <!-- Content Section -->
        <div v-else>
          <!-- Control Buttons - Always visible when not loading -->
          <div class="mb-4 flex justify-between items-center">
            <p class="text-space-gray-300">Total Events: {{ events.length }}</p>
            <div class="flex space-x-3">
              <!-- Consolidated Test Event Creation -->
              <div class="relative">
                <button
                  @click="showTestEventDropdown = !showTestEventDropdown"
                  :disabled="creatingTestEvent"
                  :class="[
                    'px-4 py-2 rounded-lg transition-colors flex items-center space-x-2',
                    creatingTestEvent
                      ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                      : 'bg-purple-600 hover:bg-purple-700 text-white'
                  ]"
                >
                  <div class="text-lg">🧪</div>
                  <span>{{ creatingTestEvent ? 'Creating...' : 'Create Test Event' }}</span>
                  <div class="text-sm" v-if="!creatingTestEvent">▼</div>
                </button>

                <!-- Dropdown Menu -->
                <div
                  v-if="showTestEventDropdown && !creatingTestEvent"
                  class="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-lg z-10 min-w-[200px]"
                  @click.stop
                >
                  <div class="py-1">
                    <button
                      v-for="eventType in testEventTypes"
                      :key="eventType.type"
                      @click="createTestEvent(eventType.type)"
                      class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center space-x-3 transition-colors"
                    >
                      <span class="text-lg">{{ eventType.icon }}</span>
                      <span>{{ eventType.label }}</span>
                    </button>
                  </div>
                </div>
              </div>
              <button 
                @click="refreshEvents" 
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <!-- Events Section -->
          <div>
            <!-- Events Table -->
            <div v-if="events.length > 0" class="bg-space-gray-700 rounded-lg overflow-hidden">
              <div class="overflow-x-auto">
                <table class="w-full">
                <thead class="bg-space-gray-600">
                  <tr>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Event ID</th>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Type</th>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Name</th>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Organizer</th>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Event Status</th>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Payroll Status</th>
                    <th class="text-left py-3 px-2 text-white font-medium whitespace-nowrap">Event Date</th>
                    <th class="text-center py-3 px-2 text-white font-medium whitespace-nowrap">Participants</th>
                    <th class="text-center py-3 px-2 text-white font-medium whitespace-nowrap">Payroll</th>
                    <th class="text-right py-3 px-2 text-white font-medium whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="event in events" 
                    :key="event.event_id"
                    class="border-b border-space-gray-600 hover:bg-space-gray-600"
                  >
                    <td class="py-3 px-2 whitespace-nowrap">
                      <code class="text-yellow-400 bg-space-gray-800 px-2 py-1 rounded text-sm">
                        {{ event.event_id }}
                      </code>
                    </td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span :class="[
                        'px-2 py-1 rounded-full text-xs font-medium inline-block',
                        {
                          'bg-blue-500 text-blue-100': event.event_type === 'mining',
                          'bg-orange-500 text-orange-100': event.event_type === 'salvage',
                          'bg-red-500 text-red-100': event.event_type === 'combat',
                          'bg-green-500 text-green-100': event.event_type === 'training',
                          'bg-purple-500 text-purple-100': event.event_type === 'cargo',
                          'bg-gray-500 text-gray-100': !['mining', 'salvage', 'combat', 'training', 'cargo'].includes(event.event_type)
                        }
                      ]">
                        {{
                          event.event_type === 'mining' ? '⛏️ Mining' :
                          event.event_type === 'salvage' ? '🔧 Salvage' :
                          event.event_type === 'combat' ? '⚔️ Combat' :
                          event.event_type === 'training' ? '🎓 Training' :
                          event.event_type === 'cargo' ? '📦 Cargo' :
                          `🏷️ ${event.event_type.charAt(0).toUpperCase() + event.event_type.slice(1)}`
                        }}
                      </span>
                    </td>
                    <td class="py-3 px-2 text-white whitespace-nowrap">{{ event.event_name || 'N/A' }}</td>
                    <td class="py-3 px-2 text-space-gray-300 whitespace-nowrap">{{ event.organizer_name || 'N/A' }}</td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span :class="[
                        'px-2 py-1 rounded-full text-xs font-medium inline-block',
                        event.status === 'open' ? 'bg-green-500 text-green-100' : 'bg-red-500 text-red-100'
                      ]">
                        {{ event.status === 'open' ? '🟢 Open' : '🔴 Closed' }}
                      </span>
                    </td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span :class="[
                        'px-2 py-1 rounded-full text-xs font-medium inline-block',
                        event.payroll_calculated ? 'bg-blue-500 text-blue-100' : 'bg-gray-500 text-gray-100'
                      ]">
                        {{ event.payroll_calculated ? '✅ Finalized' : '⏳ Pending' }}
                      </span>
                    </td>
                    <td class="py-3 px-2 text-space-gray-300 text-sm whitespace-nowrap">
                      {{ formatDate(event.started_at) }}
                    </td>
                    <td class="py-3 px-2 text-center whitespace-nowrap">
                      <span class="text-blue-400 font-mono">
                        {{ event.total_participants || 0 }}
                      </span>
                    </td>
                    <td class="py-3 px-2 text-center whitespace-nowrap">
                      <button
                        v-if="event.payroll_calculated"
                        @click="showPayrollSummary(event.event_id)"
                        class="text-green-400 hover:text-green-300 cursor-pointer transition-colors text-xs"
                        title="Click to view payroll summary"
                      >
                        ✅ View
                      </button>
                      <router-link
                        v-else
                        :to="`/?event=${event.event_id}`"
                        class="text-blue-400 hover:text-blue-300 cursor-pointer transition-colors text-xs underline"
                        title="Click to calculate payroll"
                      >
                        📊 Calculate
                      </router-link>
                    </td>
                    <td class="py-3 px-2 text-right whitespace-nowrap">
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

          <!-- No Events State -->
          <div v-else class="text-center py-8 bg-space-gray-700 rounded-lg">
            <div class="text-4xl mb-4">📋</div>
            <h3 class="text-xl font-medium text-white mb-2">No Events Found</h3>
            <p class="text-space-gray-400">No events have been created yet.</p>
          </div>
          </div>
        </div>
      </div>

      <!-- Payroll Summary Modal -->
      <div v-if="showPayrollModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div class="bg-space-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between p-6 border-b border-space-gray-700">
            <h2 class="text-2xl font-bold text-white">Payroll Summary</h2>
            <div class="flex items-center space-x-3">
              <button 
                v-if="payrollData" 
                @click="exportPDF" 
                :disabled="exportingPDF"
                :class="[
                  'px-4 py-2 rounded-lg transition-colors flex items-center space-x-2',
                  exportingPDF 
                    ? 'bg-gray-500 text-gray-300 cursor-not-allowed' 
                    : 'bg-green-600 hover:bg-green-700 text-white'
                ]"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <span>{{ exportingPDF ? 'Generating PDF...' : 'Export PDF' }}</span>
              </button>
              <button @click="showPayrollModal = false" class="text-space-gray-400 hover:text-white transition-colors">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          </div>
          <div class="p-6">
            <div v-if="loadingPayroll" class="text-center py-8">
              <div class="inline-block w-8 h-8 border-4 border-red-legion-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p class="text-space-gray-400">Loading payroll summary...</p>
            </div>
            <div v-else-if="payrollData" class="space-y-6">
              <!-- Event Overview -->
              <div class="bg-space-gray-700 rounded-lg p-4">
                <h3 class="text-lg font-semibold text-white mb-3">
                  <span class="mr-2">⛏️</span>
                  Event {{ payrollData.event_id }}
                </h3>
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="text-space-gray-400">Event ID:</span>
                    <code class="ml-2 text-yellow-400">{{ payrollData.event_id }}</code>
                  </div>
                  <div>
                    <span class="text-space-gray-400">Payroll ID:</span>
                    <span class="ml-2 text-white">{{ payrollData.payroll_id }}</span>
                  </div>
                  <div>
                    <span class="text-space-gray-400">Created:</span>
                    <span class="ml-2 text-white">{{ formatDate(payrollData.created_at) }}</span>
                  </div>
                  <div>
                    <span class="text-space-gray-400">Participants:</span>
                    <span class="ml-2 text-white">{{ payrollData.participants?.length || 0 }}</span>
                  </div>
                </div>
              </div>

              <!-- Payroll Statistics -->
              <div class="bg-space-gray-700 rounded-lg p-4">
                <h3 class="text-lg font-semibold text-white mb-3">💰 Payroll Summary</h3>
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="text-space-gray-400">Total Payout:</span>
                    <span class="ml-2 text-green-400 font-mono">{{ formatCurrency(payrollData.total_payout) }} aUEC</span>
                  </div>
                  <div>
                    <span class="text-space-gray-400">Average Payout:</span>
                    <span class="ml-2 text-blue-400 font-mono">{{ payrollData.participants?.length ? formatCurrency(payrollData.total_payout / payrollData.participants.length) : '0' }} aUEC</span>
                  </div>
                  <div>
                    <span class="text-space-gray-400">Total Participation:</span>
                    <span class="ml-2 text-white">{{ payrollData.participants ? formatDuration(payrollData.participants.reduce((sum, p) => sum + p.duration_minutes, 0)) : '0m' }}</span>
                  </div>
                  <div>
                    <span class="text-space-gray-400">Status:</span>
                    <span class="ml-2 text-green-400">Finalized</span>
                  </div>
                  <div class="col-span-2">
                    <span class="text-space-gray-400 mb-3 block">Ore Breakdown:</span>
                    <div v-if="payrollData.ore_quantities && Object.keys(payrollData.ore_quantities).some(ore => payrollData.ore_quantities[ore] > 0)" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      <div
                        v-for="(quantity, ore) in payrollData.ore_quantities"
                        v-if="quantity > 0"
                        :key="ore"
                        class="bg-space-gray-600 rounded-lg p-4 border border-space-gray-500"
                      >
                        <div class="flex justify-between items-center mb-2">
                          <h4 class="text-white font-bold text-lg">{{ ore.toUpperCase() }}</h4>
                          <span class="text-space-gray-400 text-sm">SCU</span>
                        </div>
                        <div class="space-y-1">
                          <div class="flex justify-between">
                            <span class="text-space-gray-400 text-sm">Quantity:</span>
                            <span class="text-blue-400 font-mono">{{ formatCurrency(quantity) }}</span>
                          </div>
                          <div class="flex justify-between">
                            <span class="text-space-gray-400 text-sm">Price per unit:</span>
                            <span class="text-purple-400 font-mono">{{ formatCurrency(payrollData.custom_prices[ore] || 0) }} aUEC</span>
                          </div>
                          <div class="flex justify-between pt-2 border-t border-space-gray-500">
                            <span class="text-space-gray-400 text-sm font-medium">Total Value:</span>
                            <span class="text-green-400 font-mono font-bold">{{ formatCurrency((quantity * (payrollData.custom_prices[ore] || 0))) }} aUEC</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div v-else class="text-center py-8 text-space-gray-400">
                      <div class="text-4xl mb-2">📊</div>
                      <p>No ore quantities recorded for this event</p>
                      <p class="text-sm text-space-gray-500 mt-1">Payroll calculated without ore data</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Individual Payouts -->
              <div class="bg-space-gray-700 rounded-lg p-4">
                <h3 class="text-lg font-semibold text-white mb-3">👥 Individual Payouts</h3>
                <div class="overflow-hidden rounded-lg">
                  <table class="w-full text-sm">
                    <thead class="bg-space-gray-600">
                      <tr>
                        <th class="text-left py-2 px-3 text-white font-medium">#</th>
                        <th class="text-left py-2 px-3 text-white font-medium">Participant</th>
                        <th class="text-center py-2 px-3 text-white font-medium">Time</th>
                        <th class="text-right py-2 px-3 text-white font-medium">Base Payout</th>
                        <th class="text-right py-2 px-3 text-white font-medium">Final Payout</th>
                        <th class="text-center py-2 px-3 text-white font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-space-gray-600">
                      <tr
                        v-for="(participant, index) in payrollData.participants"
                        :key="participant.username"
                        class="hover:bg-space-gray-600"
                      >
                        <td class="py-2 px-3 text-space-gray-400">{{ index + 1 }}</td>
                        <td class="py-2 px-3 text-white font-medium">{{ participant.display_name || participant.username }}</td>
                        <td class="py-2 px-3 text-center text-space-gray-300">{{ participant.duration_minutes }}m</td>
                        <td class="py-2 px-3 text-right text-blue-400 font-mono">{{ formatCurrency(participant.payout) }}</td>
                        <td class="py-2 px-3 text-right text-green-400 font-mono font-semibold">{{ formatCurrency(participant.payout) }}</td>
                        <td class="py-2 px-3 text-center">
                          <span v-if="participant.is_donating" class="text-xs bg-purple-500 text-white px-2 py-1 rounded">Donor</span>
                          <span v-else class="text-xs text-space-gray-400">Standard</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal && eventToDelete" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-space-gray-800 rounded-lg shadow-xl max-w-md w-full">
        <div class="p-6">
          <div class="flex items-center justify-center mb-4">
            <div class="bg-red-100 rounded-full p-3">
              <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
          </div>
          
          <h3 class="text-lg font-bold text-white text-center mb-2">Delete Event</h3>
          <p class="text-space-gray-300 text-center mb-6">
            Are you sure you want to delete <span class="font-bold text-white">"{{ eventToDelete.event_name }}"</span>?
          </p>
          
          <div class="bg-space-gray-900 rounded-lg p-4 mb-6">
            <p class="text-sm text-space-gray-300 mb-3">
              <strong class="text-red-400">This action will permanently delete:</strong>
            </p>
            <ul class="text-sm text-space-gray-400 space-y-1">
              <li>• The event record</li>
              <li>• All participant data</li>
              <li>• All payroll information</li>
              <li>• Any associated inventory</li>
            </ul>
            <p class="text-sm text-red-400 font-bold mt-3">❌ This action CANNOT be undone!</p>
          </div>
          
          <div class="flex space-x-3">
            <button 
              @click="cancelDelete" 
              class="flex-1 px-4 py-2 bg-space-gray-600 hover:bg-space-gray-700 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button 
              @click="confirmDelete" 
              class="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-bold"
            >
              Delete Event
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { apiService } from '../api.js'
import SystemStatus from '../components/SystemStatus.vue'

export default {
  name: 'Management',
  components: {
    SystemStatus
  },
  setup() {
    const loading = ref(true)
    const events = ref([])
    const deletingEvents = ref([])
    const creatingTestEvent = ref(false)
    const showTestEventDropdown = ref(false)
    const showPayrollModal = ref(false)
    const loadingPayroll = ref(false)
    const payrollData = ref(null)
    const exportingPDF = ref(false)
    const showDeleteModal = ref(false)
    const eventToDelete = ref(null)

    // Test event types configuration
    const testEventTypes = ref([
      { type: 'mining', label: 'Mining Operation', icon: '⛏️' },
      { type: 'salvage', label: 'Salvage Mission', icon: '🔧' },
      { type: 'combat', label: 'Combat Operation', icon: '⚔️' },
      { type: 'exploration', label: 'Exploration Mission', icon: '🗺️' },
      { type: 'trading', label: 'Trading Run', icon: '💰' },
      { type: 'social', label: 'Social Event', icon: '🎉' }
    ])

    const formatDateTime = (dateString) => {
      if (!dateString) return 'N/A'
      try {
        const date = new Date(dateString)
        return date.toLocaleString('en-US', {
          timeZone: 'UTC',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        }) + ' UTC'
      } catch (error) {
        return 'Invalid Date'
      }
    }

    const formatDate = (dateString) => {
      if (!dateString) return 'N/A'
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
          timeZone: 'UTC',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        })
      } catch (error) {
        return 'Invalid Date'
      }
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

    const formatCurrency = (amount) => {
      if (!amount) return '0'
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(Math.round(amount))
    }

    const loadEvents = async () => {
      loading.value = true
      try {
        const data = await apiService.getEvents()
        events.value = data
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

    const deleteEvent = (eventId) => {
      console.log('🔥 DELETE BUTTON CLICKED!', eventId)
      
      // Find the event to get its name for better confirmation dialog
      const event = events.value.find(e => e.event_id === eventId)
      console.log('📋 Event found:', event)
      
      // Store event to delete and show custom modal
      eventToDelete.value = event
      showDeleteModal.value = true
    }

    const confirmDelete = async () => {
      if (!eventToDelete.value) return
      
      const eventId = eventToDelete.value.event_id
      const eventName = `"${eventToDelete.value.event_name}"`
      
      showDeleteModal.value = false
      deletingEvents.value.push(eventId)
      
      try {
        const result = await apiService.deleteAdminEvent(eventId)

        // Remove the event from the local list
        events.value = events.value.filter(event => event.event_id !== eventId)

        // Show success message
        alert(`✅ SUCCESS\n\nEvent ${eventName} has been deleted successfully.\n\nAll associated data has been removed from the database.`)

      } catch (error) {
        console.error('Failed to delete event:', error)
        if (error.response?.status === 403) {
          alert('❌ Admin privileges required to delete events.\n\nThis feature is only available to administrators.')
        } else {
          alert(`❌ DELETION FAILED\n\nEvent: ${eventName}\nError: ${error.message}\n\nPlease check the browser console for more details and try again.`)
        }
      } finally {
        // Remove from deleting list
        deletingEvents.value = deletingEvents.value.filter(id => id !== eventId)
        eventToDelete.value = null
      }
    }

    const cancelDelete = () => {
      showDeleteModal.value = false
      eventToDelete.value = null
    }

    const createTestEvent = async (eventType) => {
      const validEventTypes = ['mining', 'salvage', 'combat', 'exploration', 'trading', 'social']
      if (!validEventTypes.includes(eventType)) {
        alert('Invalid event type')
        return
      }

      // Close dropdown and start creation
      showTestEventDropdown.value = false
      creatingTestEvent.value = true

      try {
        const result = await apiService.createTestEvent(eventType)
        console.log(`Test ${eventType} event created:`, result)

        // Refresh the events list to show the new test event
        await loadEvents()

        // Show success message
        alert(`✅ Test ${eventType} event "${result.event.event_name}" created successfully!\n\nEvent ID: ${result.event.event_id}\nParticipants: ${result.event.total_participants}\nDuration: ${Math.round(result.event.total_duration_minutes / 60)} hours`)

      } catch (error) {
        console.error(`Failed to create test ${eventType} event:`, error)
        if (error.response?.status === 403) {
          alert('❌ Admin privileges required to create test events.\n\nThis feature is only available to administrators.')
        } else {
          alert(`Failed to create test ${eventType} event. Please try again.\n\nError: ${error.message}`)
        }
      } finally {
        creatingTestEvent.value = false
      }
    }

    const showPayrollSummary = async (eventId) => {
      showPayrollModal.value = true
      loadingPayroll.value = true
      payrollData.value = null

      try {
        const data = await apiService.exportPayroll(eventId)
        payrollData.value = data
      } catch (error) {
        console.error('Failed to load payroll data:', error)
        alert('Failed to load payroll data. Please try again.')
      } finally {
        loadingPayroll.value = false
      }
    }

    const exportPDF = async () => {
      if (!payrollData.value) return

      exportingPDF.value = true
      try {
        // Call server-side PDF generation endpoint
        const response = await fetch(`/mgmt/api/payroll/${payrollData.value.event_id}/pdf`, {
          method: 'GET',
          headers: {
            'Accept': 'application/pdf'
          }
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        // Get the PDF blob from response
        const blob = await response.blob()

        // Create download link
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `payroll_summary_${payrollData.value.event_id}.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)

      } catch (error) {
        console.error('Failed to generate PDF:', error)
        alert('Failed to generate PDF. Please try again.')
      } finally {
        exportingPDF.value = false
      }
    }

    // Close dropdown when clicking outside
    const handleClickOutside = (event) => {
      showTestEventDropdown.value = false
    }

    onMounted(() => {
      console.log('🎯 Management component mounted successfully!')
      loadEvents()
      // Add click outside listener
      document.addEventListener('click', handleClickOutside)
    })

    onUnmounted(() => {
      // Clean up click outside listener
      document.removeEventListener('click', handleClickOutside)
    })

    return {
      loading,
      events,
      deletingEvents,
      creatingTestEvent,
      showTestEventDropdown,
      testEventTypes,
      showPayrollModal,
      loadingPayroll,
      payrollData,
      exportingPDF,
      showDeleteModal,
      eventToDelete,
      formatDateTime,
      formatDate,
      formatDuration,
      formatCurrency,
      refreshEvents,
      deleteEvent,
      confirmDelete,
      cancelDelete,
      createTestEvent,
      showPayrollSummary,
      exportPDF
    }
  }
}
</script>
<template>
  <div class="max-w-6xl mx-auto space-y-8">
    <!-- Progress Bar -->
    <div class="bg-space-gray-800 rounded-lg p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-bold text-white">Payroll Calculator</h2>
        <div class="text-sm text-space-gray-400">Step {{ currentStep }} of 5</div>
      </div>

      <!-- Event Information Bar -->
      <div v-if="selectedEvent" class="bg-space-gray-700 rounded-lg p-4 mb-4 border-l-4 border-red-legion-500">
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <h3 class="text-lg font-semibold text-white mb-1">
              {{ selectedEvent.event_name || selectedEvent.event_id }}
            </h3>
            <div class="text-space-gray-300 text-sm">
              <span class="mr-4">
                <span class="text-space-gray-400">Organizer:</span>
                {{ selectedEvent.organizer_name || 'Unknown' }}
              </span>
              <span class="mr-4">
                <span class="text-space-gray-400">Type:</span>
                {{ selectedEvent.event_type?.charAt(0).toUpperCase() + selectedEvent.event_type?.slice(1) || 'Unknown' }}
              </span>
            </div>
          </div>
          <div class="text-right">
            <div class="text-sm text-space-gray-300 font-mono">
              Event ID: {{ selectedEvent.event_id }}
            </div>
            <div class="flex items-center space-x-4 text-xs mt-1">
              <span :class="selectedEvent.ended_at ? 'text-red-400' : 'text-green-400'">
                {{ selectedEvent.ended_at ? '🔴 Ended' : '🟢 Active' }}
              </span>
              <span v-if="closingEvent" class="text-yellow-400">
                🟡 Closing...
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="flex items-center space-x-4">
        <div v-for="(step, index) in steps" :key="index" class="flex items-center">
          <div 
            :class="[
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold',
              index + 1 <= currentStep 
                ? 'bg-red-legion-500 text-white' 
                : 'bg-space-gray-600 text-space-gray-400'
            ]"
          >
            {{ index + 1 }}
          </div>
          <span 
            :class="[
              'ml-2 text-sm',
              index + 1 <= currentStep ? 'text-white' : 'text-space-gray-400'
            ]"
          >
            {{ step }}
          </span>
          <div v-if="index < steps.length - 1" class="ml-4 w-8 h-px bg-space-gray-600"></div>
        </div>
      </div>
    </div>

    <!-- Step Content -->
    <div class="min-h-96">
      <!-- Step 1: Event Selection -->
      <EventList 
        v-if="currentStep === 1" 
        @event-selected="handleEventSelected"
      />

      <!-- Step 2: Material Quantities -->
      <div v-else-if="currentStep === 2" class="bg-space-gray-800 rounded-lg shadow-xl p-6">
        <h3 class="text-xl font-semibold text-white mb-6">
          {{ selectedEvent?.event_type === 'salvage' ? 'Enter Salvage Component Quantities' : 'Enter Material Quantities' }}
        </h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div v-for="material in materialTypes" :key="material" class="space-y-2">
            <label :for="material" class="block text-sm font-medium text-space-gray-300">
              {{ material }}
            </label>
            <input
              :id="material"
              v-model.number="oreQuantities[material]"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              class="w-full px-4 py-3 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white placeholder-space-gray-400 focus:outline-none focus:ring-2 focus:ring-red-legion-500 focus:border-transparent"
            />
          </div>
        </div>

        <div class="mt-6 flex justify-between">
          <button @click="previousStep" class="px-6 py-3 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors">
            ← Previous
          </button>
          <button 
            @click="nextStep" 
            :disabled="!hasOreQuantities"
            class="px-6 py-3 bg-red-legion-600 hover:bg-red-legion-700 disabled:bg-red-legion-800 text-white rounded-lg transition-colors"
          >
            Next →
          </button>
        </div>
      </div>

      <!-- Step 3: Price Configuration -->
      <div v-else-if="currentStep === 3" class="bg-space-gray-800 rounded-lg shadow-xl p-6">
        <h3 class="text-xl font-semibold text-white mb-6">
          {{ selectedEvent?.event_type === 'salvage' ? 'Component Prices' : 'Ore Prices' }}
        </h3>
        
        <!-- Trading Location Selection -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-space-gray-300 mb-2">
            Trading Location (Optional)
          </label>
          <select 
            v-model="selectedLocationId"
            @change="handleLocationChange"
            class="w-full px-4 py-3 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-red-legion-500 focus:border-transparent"
          >
            <option value="">Average Prices (No Location)</option>
            <optgroup label="Stanton System">
              <option
                v-for="location in stantonLocations"
                :key="location.id"
                :value="location.id"
              >
                {{ location.name }} ({{ location.planet }})
              </option>
            </optgroup>
            <optgroup label="Pyro System">
              <option
                v-for="location in pyroLocations"
                :key="location.id"
                :value="location.id"
              >
                {{ location.name }} ({{ location.planet }})
              </option>
            </optgroup>
          </select>
          <p class="text-space-gray-400 text-xs mt-1">
            Select a location to use location-specific prices, or leave blank for average prices
          </p>
        </div>

        <div class="mb-6">
          <label class="flex items-center space-x-3">
            <input 
              v-model="useCustomPrices" 
              type="checkbox"
              class="w-5 h-5 text-red-legion-600 bg-space-gray-700 border-space-gray-600 rounded focus:ring-red-legion-500"
            />
            <span class="text-white">Use custom prices</span>
          </label>
          <p class="text-space-gray-400 text-sm mt-1">
            {{ useCustomPrices ? 'Enter custom prices below' : (selectedLocationId ? 'Using location-specific prices' : (selectedEvent?.event_type === 'salvage' ? 'Using default salvage prices' : 'Using default UEX prices')) }}
          </p>
        </div>

        <div v-if="materialsWithQuantities.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div v-for="material in materialsWithQuantities" :key="material" class="space-y-2">
            <div class="flex items-center justify-between">
              <label :for="`price-${material}`" class="block text-sm font-medium text-space-gray-300">
                {{ material }} Price (aUEC per SCU)
              </label>
              <div v-if="materialPriceInfo[material]" class="text-xs text-green-400 max-w-xs text-right">
                Best: {{ materialPriceInfo[material].highest_price?.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) }} aUEC/SCU<br>
                <span class="text-space-gray-400">{{ materialPriceInfo[material].best_system }} → {{ materialPriceInfo[material].best_location }}</span>
              </div>
            </div>
            <input
              :id="`price-${material}`"
              v-model.number="customPrices[material]"
              :disabled="!useCustomPrices"
              type="number"
              step="0.01"
              min="0"
              :value="useCustomPrices ? customPrices[material] : getEffectivePrice(material)"
              :placeholder="getEffectivePrice(material)?.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) || '0.00'"
              class="w-full px-4 py-3 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white placeholder-space-gray-400 focus:outline-none focus:ring-2 focus:ring-red-legion-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>
        
        <div v-else class="text-center py-8">
          <div class="text-4xl mb-4">⚠️</div>
          <h4 class="text-white font-medium mb-2">No Materials with Quantities</h4>
          <p class="text-space-gray-400">Go back to the Quantities step and enter amounts for the {{ selectedEvent?.event_type === 'salvage' ? 'components' : 'materials' }} you collected.</p>
        </div>

        <div class="mt-6 flex justify-between items-center">
          <button @click="previousStep" class="px-6 py-3 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors">
            ← Previous
          </button>
          
          <!-- Close Event Button for live events -->
          <div class="flex space-x-3 items-center">
            <button 
              v-if="selectedEvent && !selectedEvent.ended_at && !closingEvent" 
              @click="closeEvent" 
              class="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-medium"
            >
              🏁 Close Event
            </button>
            <button 
              v-else-if="closingEvent" 
              disabled 
              class="px-6 py-3 bg-gray-500 text-white rounded-lg opacity-50 font-medium"
            >
              Closing...
            </button>
          </div>

          <button @click="nextStep" class="px-6 py-3 bg-red-legion-600 hover:bg-red-legion-700 text-white rounded-lg transition-colors">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 4: Donation Settings -->
      <div v-else-if="currentStep === 4" class="bg-space-gray-800 rounded-lg shadow-xl p-6">
        <h3 class="text-xl font-semibold text-white mb-6">Participant Donations</h3>
        
        <div class="space-y-6">
          <div>
            <p class="text-space-gray-300 mb-4">
              Select participants who want to donate their entire payout. Their share will be redistributed among the remaining participants.
            </p>
            
            <div class="bg-space-gray-700 rounded-lg p-4 mb-4">
              <h4 class="text-white font-medium mb-2">💡 How donations work:</h4>
              <ul class="text-space-gray-300 text-sm space-y-1">
                <li>• Check participants who want to donate their full payout</li>
                <li>• Their entire share gets redistributed to remaining participants</li>
                <li>• Redistribution is proportional to participation time</li>
                <li>• Donating participants receive 0 aUEC payout</li>
              </ul>
            </div>
          </div>

          <div v-if="participantsLoaded && eventParticipants.length > 0">
            <h4 class="text-white font-medium mb-3">Select participants to donate:</h4>
            <div class="bg-space-gray-700 rounded-lg overflow-hidden">
              <div class="max-h-64 overflow-y-auto">
                <div 
                  v-for="participant in eventParticipants" 
                  :key="participant.user_id"
                  class="flex items-center justify-between p-3 hover:bg-space-gray-600 border-b border-space-gray-600 last:border-b-0"
                >
                  <div class="flex items-center space-x-3">
                    <input
                      :id="`donate-${participant.user_id}`"
                      v-model="participantDonations[participant.username]"
                      type="checkbox"
                      class="w-4 h-4 text-red-legion-600 bg-space-gray-600 border-space-gray-500 rounded focus:ring-red-legion-500 focus:ring-2"
                    />
                    <label :for="`donate-${participant.user_id}`" class="text-white font-medium cursor-pointer">
                      {{ participant.username }}
                    </label>
                  </div>
                  <div class="text-right text-space-gray-300 text-sm">
                    <div>{{ participant.participation_minutes }}m</div>
                    <div class="text-space-gray-400">{{ participant.participation_percentage }}%</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="mt-3 text-center">
              <span class="text-space-gray-400 text-sm">
                {{ Object.values(participantDonations).filter(d => d).length }} of {{ (eventParticipants || []).length }} participants donating
              </span>
            </div>
          </div>

          <div v-else-if="participantsLoaded && (eventParticipants || []).length === 0" class="text-center py-8">
            <div class="text-4xl mb-4">👥</div>
            <h4 class="text-white font-medium mb-2">No Participants Yet</h4>
            <p class="text-space-gray-400">No participants have been tracked for this event yet. Voice channel tracking may not have started or no one has joined the channels.</p>
          </div>

          <div v-else class="text-center py-8">
            <div class="inline-block w-6 h-6 border-2 border-red-legion-500 border-t-transparent rounded-full animate-spin mb-2"></div>
            <p class="text-space-gray-400">Loading participants...</p>
          </div>
        </div>

        <div class="mt-6 flex justify-between items-center">
          <button @click="previousStep" class="px-6 py-3 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors">
            ← Previous
          </button>
          
          <!-- Close Event Button for live events -->
          <div class="flex space-x-3 items-center">
            <button 
              v-if="selectedEvent && !selectedEvent.ended_at && !closingEvent" 
              @click="closeEvent" 
              class="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-medium"
            >
              🏁 Close Event
            </button>
            <button 
              v-else-if="closingEvent" 
              disabled 
              class="px-6 py-3 bg-gray-500 text-white rounded-lg opacity-50 font-medium"
            >
              Closing...
            </button>
          </div>

          <button @click="calculatePayroll" class="px-6 py-3 bg-red-legion-600 hover:bg-red-legion-700 text-white rounded-lg transition-colors">
            Calculate Payroll →
          </button>
        </div>
      </div>

      <!-- Step 5: Results -->
      <div v-else-if="currentStep === 5" class="space-y-6">
        <div v-if="calculating" class="bg-space-gray-800 rounded-lg shadow-xl p-8 text-center">
          <div class="inline-block w-12 h-12 border-4 border-red-legion-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p class="text-white">Calculating payroll...</p>
        </div>

        <div v-else-if="payrollResult" class="space-y-6">
          <!-- Summary -->
          <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
            <h3 class="text-xl font-semibold text-white mb-4">Payroll Summary</h3>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div class="text-center">
                <div class="text-2xl font-bold text-red-legion-500">{{ (payrollResult.total_value_auec || 0).toLocaleString() }}</div>
                <div class="text-space-gray-400 text-sm">Total Value (aUEC)</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-purple-500">{{ (payrollResult.total_scu || totalSCU || 0).toLocaleString() }}</div>
                <div class="text-space-gray-400 text-sm">Total SCU</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-blue-500">{{ (payrollResult.payouts || []).length }}</div>
                <div class="text-space-gray-400 text-sm">Participants</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-green-500">{{ selectedEvent.event_name || selectedEvent.event_id }}</div>
                <div class="text-space-gray-400 text-sm">Event</div>
              </div>
            </div>
          </div>

          <!-- Material/Ore Breakdown -->
          <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
            <h3 class="text-xl font-semibold text-white mb-4">
              {{ selectedEvent?.event_type === 'salvage' ? '🔧 Salvage Components Collected' : '⛏️ Ore Mined' }}
            </h3>
            <div v-if="Object.keys(oreQuantities).length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div 
                v-for="(quantity, material) in oreQuantities" 
                :key="material"
                v-show="quantity > 0"
                class="bg-space-gray-700 rounded-lg p-4"
              >
                <div class="flex justify-between items-center mb-2">
                  <h4 class="font-medium text-white text-sm">{{ material }}</h4>
                  <span class="text-xs text-space-gray-400">{{ selectedEvent?.event_type === 'salvage' ? 'Components' : 'SCU' }}</span>
                </div>
                <div class="space-y-1">
                  <div class="flex justify-between">
                    <span class="text-space-gray-400 text-sm">Quantity:</span>
                    <span class="text-blue-400 font-mono">{{ (quantity || 0).toLocaleString() }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-space-gray-400 text-sm">Price per unit:</span>
                    <span class="text-purple-400 font-mono">{{ (getEffectivePrice(material) || 0).toLocaleString() }} aUEC</span>
                  </div>
                  <div class="flex justify-between border-t border-space-gray-600 pt-1">
                    <span class="text-white text-sm font-medium">Total Value:</span>
                    <span class="text-green-400 font-mono font-bold">{{ ((quantity || 0) * (getEffectivePrice(material) || 0)).toLocaleString() }} aUEC</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-8">
              <div class="text-4xl mb-2">📦</div>
              <p class="text-space-gray-400">No {{ selectedEvent?.event_type === 'salvage' ? 'components' : 'materials' }} recorded</p>
            </div>
          </div>

          <!-- Participant Payouts -->
          <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
            <h3 class="text-xl font-semibold text-white mb-4">Individual Payouts</h3>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-space-gray-600">
                    <th class="text-left py-3 text-space-gray-300">Participant</th>
                    <th class="text-right py-3 text-space-gray-300">Time</th>
                    <th class="text-right py-3 text-space-gray-300">%</th>
                    <th class="text-right py-3 text-space-gray-300">Payout (aUEC)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="payout in (payrollResult.payouts || [])" :key="payout.user_id" class="border-b border-space-gray-700">
                    <td class="py-3 text-white">{{ payout.username }}</td>
                    <td class="py-3 text-right text-space-gray-300">{{ payout.participation_minutes }}m</td>
                    <td class="py-3 text-right text-space-gray-300">{{ (payout.participation_percentage || 0).toFixed(1) }}%</td>
                    <td class="py-3 text-right text-green-500 font-mono">{{ (payout.final_payout_auec || 0).toLocaleString() }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex justify-between items-center">
            <button @click="startOver" class="px-6 py-3 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors">
              ← Start Over
            </button>
            
            <div class="flex space-x-3 items-center">
              <!-- Close Event Button (only show for live events) -->
              <button 
                v-if="selectedEvent && !selectedEvent.ended_at && !closingEvent" 
                @click="closeEvent" 
                class="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-medium"
              >
                🏁 Close Event
              </button>
              <!-- Close Payroll Button (for ended events) -->
              <button 
                v-else-if="selectedEvent && selectedEvent.ended_at" 
                @click="closePayroll" 
                class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
              >
                📋 Close Payroll
              </button>
              <button 
                v-else-if="closingEvent" 
                disabled 
                class="px-6 py-3 bg-gray-500 text-white rounded-lg opacity-50 font-medium"
              >
                Closing...
              </button>
              
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { apiService } from '../api.js'
import EventList from './EventList.vue'

export default {
  name: 'PayrollWizard',
  components: {
    EventList
  },
  props: {
    user: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const currentStep = ref(1)
    const steps = ['Select Event', 'Quantities', 'Price Setup', 'Donations', 'Results']
    
    const selectedEvent = ref(null)
    const oreQuantities = ref({})
    const useCustomPrices = ref(false)
    const customPrices = ref({})
    const defaultPrices = ref({})
    const defaultDonationPercentage = ref(0)
    const participantDonations = ref({})
    const eventParticipants = ref([])
    const participantsLoaded = ref(false)
    const calculating = ref(false)
    const payrollResult = ref(null)
    const closingEvent = ref(false)
    
    // Trading location state
    const tradingLocations = ref([])
    const selectedLocationId = ref(4) // Default to Orison (best prices for most materials)
    const materialPriceInfo = ref({})
    const loadingLocations = ref(false)

    const miningOreTypes = [
      // Major ores (high-value)
      'QUANTAINIUM',
      'BEXALITE',
      'TARANITE',
      'BORASE',
      'LARANITE',
      'AGRICIUM',
      'HEPHAESTANITE',
      'RICCITE',
      'STILERON',
      'GOLDEN MEDMON',

      // Gemstones (high-value)
      'HADANITE',
      'JANALITE',
      'APHORITE',
      'DOLIVINE',
      'DIAMOND',
      'BERYL',

      // Common metals
      'TITANIUM',
      'GOLD',
      'COPPER',
      'TUNGSTEN',
      'ALUMINUM',
      'IRON',
      'TIN',
      'SILICON',

      // Low-value materials
      'CORUNDUM',
      'QUARTZ',
      'ASTATINE',

      // Special materials
      'HEXAPOLYMESH COATING',
      'INERT_MATERIALS'
    ]

    const salvageComponentTypes = [
      'RECYCLED MATERIAL COMPOSITE',
      'CONSTRUCTION MATERIALS'
    ]

    // Computed property to get materials based on event type
    const materialTypes = computed(() => {
      if (selectedEvent.value?.event_type === 'salvage') {
        return salvageComponentTypes
      }
      return miningOreTypes
    })

    // Computed properties to group locations by system
    const stantonLocations = computed(() => {
      return tradingLocations.value.filter(location => location.system === 'Stanton')
    })

    const pyroLocations = computed(() => {
      return tradingLocations.value.filter(location => location.system === 'Pyro')
    })

    // Computed property to calculate total SCU from all materials with quantities
    const totalSCU = computed(() => {
      return Object.values(oreQuantities.value)
        .reduce((total, quantity) => total + (Number(quantity) || 0), 0)
    })

    // Initialize material quantities and prices - update when event changes
    const initializeMaterials = () => {
      const materials = materialTypes.value
      const newQuantities = {}
      const newPrices = {}
      
      materials.forEach(material => {
        newQuantities[material] = oreQuantities.value[material] || 0
        // Preserve existing prices or use default prices if available, otherwise 0
        newPrices[material] = customPrices.value[material] || defaultPrices.value[material] || 0
      })
      
      oreQuantities.value = newQuantities
      customPrices.value = newPrices
    }
    
    // Load trading locations on component mount
    const loadTradingLocations = async () => {
      if (tradingLocations.value.length > 0) return // Already loaded
      
      loadingLocations.value = true
      try {
        tradingLocations.value = await apiService.getTradingLocations()
      } catch (error) {
        console.error('Failed to load trading locations:', error)
      } finally {
        loadingLocations.value = false
      }
    }
    
    // Load material price info for materials with quantities
    const loadMaterialPriceInfo = async () => {
      const materialsWithQuantities = Object.keys(oreQuantities.value)
        .filter(material => oreQuantities.value[material] > 0)
      
      if (materialsWithQuantities.length === 0) {
        materialPriceInfo.value = {}
        return
      }
      
      try {
        const priceData = await apiService.getMaterialPrices(materialsWithQuantities)
        const priceMap = {}
        priceData.forEach(item => {
          priceMap[item.material_name] = {
            highest_price: item.highest_price,
            best_location: item.best_location,
            best_system: item.best_system,
            best_station: item.best_station
          }
        })
        materialPriceInfo.value = priceMap
      } catch (error) {
        console.error('Failed to load material price info:', error)
      }
    }
    
    // Get materials that have quantities entered (for location-specific pricing)
    const materialsWithQuantities = computed(() => {
      return Object.keys(oreQuantities.value)
        .filter(material => oreQuantities.value[material] > 0)
    })
    
    // Watch for changes in materialsWithQuantities to refresh price info
    watch(materialsWithQuantities, async () => {
      if (currentStep.value === 3) {
        await loadMaterialPriceInfo()
      }
    }, { deep: true })
    
    // Handle location selection change
    const handleLocationChange = async () => {
      if (!selectedLocationId.value) {
        // Reset to UEX default prices when no location selected
        try {
          defaultPrices.value = await apiService.getUexPrices()
          if (!useCustomPrices.value) {
            initializeMaterials()
          }
        } catch (error) {
          console.error('Failed to reset to UEX prices:', error)
        }
        return
      }
      
      // Get location-specific prices ONLY for materials that have quantities entered
      const materialsToUpdate = materialsWithQuantities.value
      
      if (materialsToUpdate.length === 0) return
      
      try {
        const locationPrices = await apiService.getMaterialPrices(materialsToUpdate, selectedLocationId.value)
        
        // Update default prices with location-specific prices
        const newDefaultPrices = { ...defaultPrices.value }
        locationPrices.forEach(item => {
          // Backend returns 'price' property for location-specific prices
          newDefaultPrices[item.material_name] = item.price
        })
        defaultPrices.value = newDefaultPrices

        // Update the actual price fields immediately if not using custom prices
        if (!useCustomPrices.value) {
          const newPrices = { ...customPrices.value }
          locationPrices.forEach(item => {
            newPrices[item.material_name] = item.price
          })
          customPrices.value = newPrices
        }
      } catch (error) {
        console.error('Failed to load location-specific prices:', error)
      }
    }
    
    // Get effective price for display (custom, location-specific, or default)
    const getEffectivePrice = (material) => {
      // Use custom price if custom prices are enabled and the material has a custom price
      if (useCustomPrices.value && customPrices.value[material]) {
        return customPrices.value[material]
      }
      // Use location-specific price if available
      if (selectedLocationId.value && defaultPrices.value[material]) {
        return defaultPrices.value[material]
      }
      // Fall back to default price
      return defaultPrices.value[material] || 0
    }

    const hasOreQuantities = computed(() => {
      return Object.values(oreQuantities.value).some(qty => qty > 0)
    })

    const handleEventSelected = (event) => {
      selectedEvent.value = event
      
      // Clear previous state when selecting a new event
      payrollResult.value = null
      participantDonations.value = {}
      eventParticipants.value = []
      participantsLoaded.value = false
      useCustomPrices.value = false
      
      // Initialize materials based on event type
      initializeMaterials()
      
      nextStep()
    }

    const nextStep = async () => {
      if (currentStep.value < 5) {
        currentStep.value++
        
        // Load prices and locations when entering step 3 (Price Setup)
        if (currentStep.value === 3) {
          // Load default prices if not already loaded
          if (Object.keys(defaultPrices.value).length === 0) {
            try {
              // Load prices from UEX API for both mining and salvage events
              defaultPrices.value = await apiService.getUexPrices()
              
              // Re-initialize materials to apply the default prices
              initializeMaterials()
            } catch (error) {
              console.error('Failed to load prices:', error)
            }
          }
          
          // Load trading locations
          await loadTradingLocations()
          
          // Load material price info for materials with quantities
          await loadMaterialPriceInfo()
          
          // Trigger location change to load Orison prices if Orison is selected by default
          if (selectedLocationId.value === 4) {
            await handleLocationChange()
          }
        }
        
        // Load participants when entering step 4 (Donations)
        if (currentStep.value === 4 && selectedEvent.value && !participantsLoaded.value) {
          try {
            eventParticipants.value = await apiService.getEventParticipants(selectedEvent.value.event_id)
            participantsLoaded.value = true
            // Initialize donation checkboxes (all unchecked by default) - use usernames for stability
            const newDonations = {}
            eventParticipants.value.forEach(participant => {
              newDonations[participant.username] = false
            })
            participantDonations.value = newDonations
          } catch (error) {
            console.error('Failed to load participants:', error)
            participantsLoaded.value = true // Mark as loaded even on error to prevent infinite retries
          }
        }
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    const calculatePayroll = async () => {
      calculating.value = true
      currentStep.value = 5

      try {
        // Get default prices
        defaultPrices.value = await apiService.getUexPrices()

        // Prepare prices - always send effective prices for calculation
        let prices = {}
        if (useCustomPrices.value) {
          prices = customPrices.value
        } else {
          // Use effective prices (default UEX prices or location-specific)
          for (const material of materialsWithQuantities.value) {
            prices[material] = getEffectivePrice(material)
          }
        }
        
        // Prepare donation data - convert usernames to user_ids
        const donatingUsernames = Object.entries(participantDonations.value)
          .filter(([username, isDonating]) => isDonating)
          .map(([username]) => username)

        // Convert usernames to current user_ids
        const donatingUsers = donatingUsernames.map(username => {
          const participant = eventParticipants.value.find(p => p.username === username)
          return participant ? String(participant.user_id) : null
        }).filter(Boolean) // Remove any null values
        
        // Debug logging
        console.log('🔍 Debug - Donating usernames:', donatingUsernames)
        console.log('🔍 Debug - Donating user IDs being sent:', donatingUsers)
        
        // Calculate payroll
        const result = await apiService.calculatePayroll(
          selectedEvent.value.event_id,
          oreQuantities.value,
          prices,
          donatingUsers
        )

        // Transform the backend response to match frontend expectations
        if (result.participants) {
          console.log('🔍 Debug - Backend participants response:', result.participants)

          // Transform participants to payouts format
          result.payouts = result.participants.map(participant => {
            const transformedParticipant = {
              user_id: participant.user_id,
              username: participant.username,
              display_name: participant.display_name,
              participation_minutes: participant.duration_minutes,
              participation_percentage: participant.duration_minutes ?
                (participant.duration_minutes / result.total_duration_minutes * 100) : 0,
              final_payout_auec: participant.payout || 0,
              is_donating: participant.is_donating || false
            }

            console.log(`🔍 Debug - Transformed ${participant.username}: payout=${participant.payout}, is_donating=${participant.is_donating}, final_payout_auec=${transformedParticipant.final_payout_auec}`)

            return transformedParticipant
          })

          // Set total value from backend calculation
          result.total_value_auec = result.total_payout || 0
          result.total_scu = Object.values(oreQuantities.value).reduce((sum, qty) => sum + (qty || 0), 0)
        }

        payrollResult.value = result
      } catch (error) {
        console.error('Payroll calculation failed:', error)
        alert('Failed to calculate payroll: ' + (error.response?.data?.detail || error.message))
      } finally {
        calculating.value = false
      }
    }

    const closeEvent = async () => {
      if (!selectedEvent.value || selectedEvent.value.ended_at) return
      
      closingEvent.value = true
      
      try {
        // First, close the event in the website backend (updates database)
        const result = await apiService.closeEvent(selectedEvent.value.event_id)
        
        // Then, stop Discord voice tracking
        try {
          console.log('🛑 Stopping Discord voice tracking...')
          const discordResponse = await fetch(`http://localhost:8001/events/${selectedEvent.value.event_id}/stop`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            }
          })
          
          if (discordResponse.ok) {
            const discordResult = await discordResponse.json()
            console.log('✅ Discord voice tracking stopped:', discordResult)
          } else {
            const errorText = await discordResponse.text()
            console.error('❌ Failed to stop Discord voice tracking:', errorText)
          }
        } catch (discordError) {
          console.error('❌ Discord API error:', discordError)
        }
        
        // Update the selectedEvent to reflect that it's now closed
        selectedEvent.value.ended_at = new Date().toISOString()
        selectedEvent.value.status = 'closed'
        selectedEvent.value.total_participants = result.total_participants
        selectedEvent.value.total_duration_minutes = result.total_duration_minutes
        
        alert(`Event ${selectedEvent.value.event_id} has been closed successfully!\n\n` +
              `Final Stats:\n` +
              `• ${result.total_participants} participants\n` +
              `• ${result.total_duration_minutes} minutes duration\n` +
              `• Voice tracking stopped`)
        
      } catch (error) {
        console.error('Failed to close event:', error)
        alert('Failed to close event: ' + (error.response?.data?.detail || error.message))
      } finally {
        closingEvent.value = false
      }
    }

    const closePayroll = async () => {
      if (!selectedEvent.value || !payrollResult.value) return
      
      closingEvent.value = true
      
      try {
        // Get the current payroll calculation data
        const donatingUsers = Object.entries(participantDonations.value)
          .filter(([userId, isDonating]) => isDonating)
          .map(([userId]) => String(userId)) // Ensure user_id is converted to string
        
        // Prepare prices - always send effective prices for calculation
        let prices = {}
        if (useCustomPrices.value) {
          prices = customPrices.value
        } else {
          // Use effective prices (default UEX prices or location-specific)
          for (const material of materialsWithQuantities.value) {
            prices[material] = getEffectivePrice(material)
          }
        }
        
        const result = await apiService.finalizePayroll(
          selectedEvent.value.event_id,
          oreQuantities.value,
          prices,
          donatingUsers
        )
        
        alert(`Payroll ${result.payroll_id} has been finalized and saved to database!\n\n` +
              `Event: ${selectedEvent.value.event_id}\n` +
              `Total Value: ${(payrollResult.value.total_value_auec || 0).toLocaleString()} aUEC\n` +
              `Payouts: ${(payrollResult.value.payouts || []).length} participants`)
        
        // Reset to home screen after successful archiving
        startOver()
        
      } catch (error) {
        console.error('Failed to finalize payroll:', error)
        alert('Failed to finalize payroll: ' + (error.response?.data?.detail || error.message))
      } finally {
        closingEvent.value = false
      }
    }

    const startOver = () => {
      currentStep.value = 1
      selectedEvent.value = null
      payrollResult.value = null
      participantsLoaded.value = false
      // Reset quantities
      oreQuantities.value = {}
      customPrices.value = {}
      useCustomPrices.value = false
      defaultPrices.value = {}
    }


    return {
      currentStep,
      steps,
      selectedEvent,
      oreQuantities,
      materialTypes,
      useCustomPrices,
      customPrices,
      defaultPrices,
      defaultDonationPercentage,
      participantDonations,
      eventParticipants,
      participantsLoaded,
      calculating,
      payrollResult,
      closingEvent,
      hasOreQuantities,
      handleEventSelected,
      nextStep,
      previousStep,
      calculatePayroll,
      closeEvent,
      closePayroll,
      startOver,
      tradingLocations,
      selectedLocationId,
      materialPriceInfo,
      loadingLocations,
      handleLocationChange,
      getEffectivePrice,
      stantonLocations,
      pyroLocations,
      materialsWithQuantities,
      totalSCU
    }
  }
}
</script>
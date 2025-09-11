<template>
  <div class="max-w-6xl mx-auto space-y-8">
    <!-- Progress Bar -->
    <div class="bg-space-gray-800 rounded-lg p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-bold text-white">Payroll Calculator</h2>
        <div class="text-sm text-space-gray-400">Step {{ currentStep }} of 4</div>
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

      <!-- Step 2: Ore Quantities -->
      <div v-else-if="currentStep === 2" class="bg-space-gray-800 rounded-lg shadow-xl p-6">
        <h3 class="text-xl font-semibold text-white mb-6">Enter Ore Quantities</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div v-for="ore in oreTypes" :key="ore" class="space-y-2">
            <label :for="ore" class="block text-sm font-medium text-space-gray-300">
              {{ ore }}
            </label>
            <input
              :id="ore"
              v-model.number="oreQuantities[ore]"
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
        <h3 class="text-xl font-semibold text-white mb-6">Ore Prices</h3>
        
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
            {{ useCustomPrices ? 'Enter custom prices below' : 'Using default UEX prices' }}
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div v-for="ore in oreTypes" :key="ore" class="space-y-2">
            <label :for="`price-${ore}`" class="block text-sm font-medium text-space-gray-300">
              {{ ore }} Price (aUEC)
            </label>
            <input
              :id="`price-${ore}`"
              v-model.number="customPrices[ore]"
              :disabled="!useCustomPrices"
              type="number"
              step="0.01"
              min="0"
              :placeholder="defaultPrices[ore]?.toLocaleString() || '0'"
              class="w-full px-4 py-3 bg-space-gray-700 border border-space-gray-600 rounded-lg text-white placeholder-space-gray-400 focus:outline-none focus:ring-2 focus:ring-red-legion-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        <div class="mt-6 flex justify-between">
          <button @click="previousStep" class="px-6 py-3 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors">
            ← Previous
          </button>
          <button @click="calculatePayroll" class="px-6 py-3 bg-red-legion-600 hover:bg-red-legion-700 text-white rounded-lg transition-colors">
            Calculate Payroll →
          </button>
        </div>
      </div>

      <!-- Step 4: Results -->
      <div v-else-if="currentStep === 4" class="space-y-6">
        <div v-if="calculating" class="bg-space-gray-800 rounded-lg shadow-xl p-8 text-center">
          <div class="inline-block w-12 h-12 border-4 border-red-legion-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p class="text-white">Calculating payroll...</p>
        </div>

        <div v-else-if="payrollResult" class="space-y-6">
          <!-- Summary -->
          <div class="bg-space-gray-800 rounded-lg shadow-xl p-6">
            <h3 class="text-xl font-semibold text-white mb-4">Payroll Summary</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div class="text-center">
                <div class="text-2xl font-bold text-red-legion-500">{{ payrollResult.total_value_auec.toLocaleString() }}</div>
                <div class="text-space-gray-400 text-sm">Total Value (aUEC)</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-blue-500">{{ payrollResult.payouts.length }}</div>
                <div class="text-space-gray-400 text-sm">Participants</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-green-500">{{ selectedEvent.event_name || selectedEvent.event_id }}</div>
                <div class="text-space-gray-400 text-sm">Event</div>
              </div>
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
                  <tr v-for="payout in payrollResult.payouts" :key="payout.user_id" class="border-b border-space-gray-700">
                    <td class="py-3 text-white">{{ payout.username }}</td>
                    <td class="py-3 text-right text-space-gray-300">{{ payout.participation_minutes }}m</td>
                    <td class="py-3 text-right text-space-gray-300">{{ payout.participation_percentage.toFixed(1) }}%</td>
                    <td class="py-3 text-right text-green-500 font-mono">{{ payout.final_payout_auec.toLocaleString() }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex justify-between">
            <button @click="startOver" class="px-6 py-3 bg-space-gray-600 hover:bg-space-gray-500 text-white rounded-lg transition-colors">
              ← Start Over
            </button>
            <button @click="exportResults" class="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
              📊 Export Results
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
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
  setup() {
    const currentStep = ref(1)
    const steps = ['Select Event', 'Ore Quantities', 'Price Setup', 'Results']
    
    const selectedEvent = ref(null)
    const oreQuantities = ref({})
    const useCustomPrices = ref(false)
    const customPrices = ref({})
    const defaultPrices = ref({})
    const calculating = ref(false)
    const payrollResult = ref(null)

    const oreTypes = [
      'QUANTAINIUM',
      'GOLD', 
      'COPPER',
      'RICCITE',
      'CORUNDUM'
    ]

    // Initialize ore quantities and prices
    oreTypes.forEach(ore => {
      oreQuantities.value[ore] = 0
      customPrices.value[ore] = 0
    })

    const hasOreQuantities = computed(() => {
      return Object.values(oreQuantities.value).some(qty => qty > 0)
    })

    const handleEventSelected = (event) => {
      selectedEvent.value = event
      nextStep()
    }

    const nextStep = () => {
      if (currentStep.value < 4) {
        currentStep.value++
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    const calculatePayroll = async () => {
      calculating.value = true
      currentStep.value = 4

      try {
        // Get default prices
        defaultPrices.value = await apiService.getUexPrices()
        
        // Prepare prices
        const prices = useCustomPrices.value ? customPrices.value : null
        
        // Calculate payroll
        const result = await apiService.calculatePayroll(
          selectedEvent.value.event_id,
          oreQuantities.value,
          prices
        )
        
        payrollResult.value = result
      } catch (error) {
        console.error('Payroll calculation failed:', error)
        alert('Failed to calculate payroll: ' + (error.response?.data?.detail || error.message))
      } finally {
        calculating.value = false
      }
    }

    const startOver = () => {
      currentStep.value = 1
      selectedEvent.value = null
      payrollResult.value = null
      // Reset quantities
      oreTypes.forEach(ore => {
        oreQuantities.value[ore] = 0
        customPrices.value[ore] = 0
      })
      useCustomPrices.value = false
    }

    const exportResults = () => {
      if (!payrollResult.value) return
      
      // Create CSV content
      const headers = ['Username', 'User ID', 'Minutes', 'Percentage', 'Payout (aUEC)']
      const rows = payrollResult.value.payouts.map(payout => [
        payout.username,
        payout.user_id,
        payout.participation_minutes,
        payout.participation_percentage.toFixed(2),
        payout.final_payout_auec.toFixed(2)
      ])
      
      const csvContent = [headers, ...rows]
        .map(row => row.map(cell => `"${cell}"`).join(','))
        .join('\n')
      
      // Download file
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `payroll-${selectedEvent.value.event_id}-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    }

    return {
      currentStep,
      steps,
      selectedEvent,
      oreQuantities,
      oreTypes,
      useCustomPrices,
      customPrices,
      defaultPrices,
      calculating,
      payrollResult,
      hasOreQuantities,
      handleEventSelected,
      nextStep,
      previousStep,
      calculatePayroll,
      startOver,
      exportResults
    }
  }
}
</script>
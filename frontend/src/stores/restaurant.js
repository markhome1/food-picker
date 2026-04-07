import { defineStore } from 'pinia'
import { ref } from 'vue'
import { restaurantApi } from '../api'

export const useRestaurantStore = defineStore('restaurant', () => {
  const list = ref([])
  const loading = ref(false)
  const filters = ref({
    price_tier: '',
    category: '',
    keyword: '',
    max_distance_km: '',
    sort_by: 'name',
    user_lat: null,
    user_lng: null,
  })

  const fetchList = async () => {
    loading.value = true
    try {
      const params = {}
      Object.entries(filters.value).forEach(([k, v]) => {
        if (v !== '' && v !== null) params[k] = v
      })
      list.value = await restaurantApi.list(params)
    } catch (e) {
      console.error(e)
    } finally {
      loading.value = false
    }
  }

  return { list, loading, filters, fetchList }
})

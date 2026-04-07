<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <view id="food-picker-amap" class="amap-box" />
    <view class="bar">
      <text class="tip">点击地图选择位置，再点「确认」</text>
      <text v-if="addrPreview" class="addr">{{ addrPreview }}</text>
      <view class="actions">
        <view class="btn ghost" @click="onCancel"><text class="btn-t">取消</text></view>
        <view class="btn primary" @click="onConfirm"><text class="btn-t light">确认位置</text></view>
      </view>
    </view>
    <!-- #endif -->
    <!-- #ifndef H5 -->
    <view class="fallback"><text class="fallback-t">请返回并使用系统地图选点</text></view>
    <!-- #endif -->
  </view>
</template>

<script setup>
import { ref, getCurrentInstance, onMounted } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'

/** 成信大航空港附近默认中心 GCJ-02 */
const DEFAULT_CENTER = [103.9986, 30.5865]

const addrPreview = ref('')
const pickedLng = ref(null)
const pickedLat = ref(null)

let eventChannel = null
let map = null
let marker = null

onLoad(() => {
  // #ifndef H5
  uni.navigateBack()
  // #endif
})

function getAmapCredentials() {
  // eslint-disable-next-line no-undef
  const cfg = typeof __uniConfig !== 'undefined' ? __uniConfig : {}
  return {
    key: cfg.aMapKey || '',
    securityJsCode: cfg.aMapSecurityJsCode || '',
  }
}

function loadAmapScript(key, securityJsCode) {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'))
  window._AMapSecurityConfig = { securityJsCode }
  return new Promise((resolve, reject) => {
    if (window.AMap) {
      resolve()
      return
    }
    const s = document.createElement('script')
    s.async = true
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}&plugin=AMap.Geocoder`
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('高德地图脚本加载失败'))
    document.head.appendChild(s)
  })
}

function reverseGeocode(lng, lat) {
  if (!window.AMap || !map) return
  window.AMap.plugin('AMap.Geocoder', () => {
    const geocoder = new window.AMap.Geocoder()
    geocoder.getAddress([lng, lat], (status, result) => {
      if (status === 'complete' && result?.regeocode) {
        addrPreview.value = result.regeocode.formattedAddress || ''
      }
    })
  })
}

// #ifdef H5
onMounted(async () => {
  const proxy = getCurrentInstance()?.proxy
  if (proxy && typeof proxy.getOpenerEventChannel === 'function') {
    eventChannel = proxy.getOpenerEventChannel()
  }

  const { key, securityJsCode } = getAmapCredentials()
  if (!key || !securityJsCode) {
    uni.showToast({
      title: '请在 manifest.json → h5.sdkConfigs.maps.amap 填写 Key 与安全密钥',
      icon: 'none',
      duration: 4000,
    })
    return
  }
  try {
    await loadAmapScript(key, securityJsCode)
  } catch {
    uni.showToast({ title: '地图加载失败，请检查 Key / 域名白名单', icon: 'none', duration: 3500 })
    return
  }

  await new Promise((r) => setTimeout(r, 0))

  map = new window.AMap.Map('food-picker-amap', {
    zoom: 16,
    center: DEFAULT_CENTER,
    viewMode: '2D',
  })

  marker = new window.AMap.Marker({ position: DEFAULT_CENTER, map })
  pickedLng.value = DEFAULT_CENTER[0]
  pickedLat.value = DEFAULT_CENTER[1]
  reverseGeocode(DEFAULT_CENTER[0], DEFAULT_CENTER[1])

  map.on('click', (e) => {
    const lng = e.lnglat.getLng()
    const lat = e.lnglat.getLat()
    pickedLng.value = lng
    pickedLat.value = lat
    marker.setPosition(e.lnglat)
    addrPreview.value = ''
    reverseGeocode(lng, lat)
  })
})
// #endif

onUnload(() => {
  // #ifdef H5
  if (map) {
    map.destroy()
    map = null
    marker = null
  }
  // #endif
})

function onCancel() {
  uni.navigateBack()
}

function onConfirm() {
  // #ifndef H5
  uni.navigateBack()
  return
  // #endif
  if (pickedLng.value == null || pickedLat.value == null) {
    uni.showToast({ title: '请在地图上点击选择位置', icon: 'none' })
    return
  }
  if (eventChannel) {
    eventChannel.emit('pickLocation', {
      latitude: pickedLat.value,
      longitude: pickedLng.value,
      name: '',
      address: addrPreview.value || '地图选点',
    })
  }
  uni.navigateBack()
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #1c1917;
  display: flex;
  flex-direction: column;
}
/* #ifdef H5 */
.amap-box {
  flex: 1;
  width: 100%;
  min-height: 55vh;
}
.bar {
  flex-shrink: 0;
  padding: 24rpx 32rpx calc(24rpx + env(safe-area-inset-bottom));
  background: #fafaf9;
  border-radius: 32rpx 32rpx 0 0;
  margin-top: -24rpx;
  position: relative;
  z-index: 2;
}
.tip {
  display: block;
  font-size: 26rpx;
  color: #57534e;
  margin-bottom: 12rpx;
}
.addr {
  display: block;
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.45;
  margin-bottom: 20rpx;
  max-height: 120rpx;
  overflow: hidden;
}
.actions {
  display: flex;
  flex-direction: row;
  gap: 20rpx;
}
.btn {
  flex: 1;
  padding: 24rpx 32rpx;
  border-radius: 9999rpx;
  text-align: center;
}
.btn-t {
  font-size: 30rpx;
  font-weight: 600;
  color: #44403c;
}
.btn-t.light {
  color: #fff;
}
.ghost {
  background: #e7e5e4;
}
.primary {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
}
/* #endif */
.fallback {
  padding: 120rpx 48rpx;
  align-items: center;
}
.fallback-t {
  font-size: 28rpx;
  color: #a8a29e;
}
</style>

<template>
  <view class="page">
    <text class="hint">
      H5：尽量<strong>点到店名图标</strong>；若多家店很近会弹出列表请选准。也可拖地图对准十字准心后「搜附近好店」或关键词搜索，底部「加入自己精选」。
    </text>

    <view v-if="!isH5" class="nh5-tip">
      <text>当前端为小程序/App：请用关键词搜索；地图选附近仅浏览器 H5 支持。</text>
    </view>

    <view class="search-row">
      <input
        class="search-input"
        v-model="keyword"
        placeholder="关键词：建设路火锅、咖啡…"
        confirm-type="search"
        @confirm="doSearch"
      />
      <view class="search-btn" @click="doSearch"><text class="search-btn-t">搜索</text></view>
    </view>

    <view v-if="isH5" class="nearby-bar">
      <view class="radius-row">
        <text class="radius-label">附近半径</text>
        <view
          v-for="r in radiusOptions"
          :key="r"
          :class="['radius-chip', nearbyRadius === r ? 'radius-on' : '']"
          @click="nearbyRadius = r"
        >
          <text>{{ r / 1000 }}km</text>
        </view>
      </view>
      <view class="nearby-actions">
        <view class="nbtn outline" @click="recenterGps"><text class="nbtn-t">定位到当前位置</text></view>
        <view class="nbtn primary" @click="doNearby"><text class="nbtn-t">搜附近好店</text></view>
      </view>
    </view>

    <view v-if="isH5" class="map-wrap">
      <view class="map-stage">
        <view id="batch-amap" class="batch-amap"></view>
        <view v-if="mapLoading" class="map-loading-mask">
          <text class="map-loading-text">地图加载中…</text>
        </view>
        <view class="map-cross" aria-hidden="true">
          <view class="cross-v"></view>
          <view class="cross-h"></view>
          <view class="cross-dot"></view>
        </view>
      </view>
      <text class="map-tip">准心即搜索中心 · 拖动地图调整</text>
      <view class="steps-bar">
        <text class="steps-text">① 点「搜附近好店」加载列表 → ② 在下方勾选店铺 → ③ 底部点「加入自己精选」</text>
      </view>
    </view>

    <view v-if="loading" class="loading"><text>{{ loadingText }}</text></view>

    <scroll-view v-else :class="['list', isH5 ? 'list-with-map' : '']" scroll-y :show-scrollbar="true">
      <view v-if="!searched" class="list-placeholder">
        <text class="list-placeholder-t">可点击地图上店铺附近拾取，或点「搜附近好店」/关键词搜索；列表里点行勾选，最下方「加入自己精选」。</text>
      </view>
      <view
        v-for="(p, idx) in results"
        :key="idx + '-' + p.name"
        :class="['row', selected.has(idx) ? 'row-on' : '']"
        @click="toggle(idx)"
      >
        <view class="row-check">
          <text class="idx-badge">{{ idx + 1 }}</text>
          <text class="check-icon">{{ selected.has(idx) ? '☑' : '☐' }}</text>
        </view>
        <image v-if="p.image_url" class="row-img" :src="p.image_url" mode="aspectFill" />
        <view v-else class="row-img row-img-ph"></view>
        <view class="row-body">
          <text class="row-name">{{ p.name }}</text>
          <text class="row-addr">{{ p.address || '—' }}</text>
          <view class="row-meta">
            <text v-if="p.rating" class="meta">{{ p.rating }}★</text>
            <text v-if="p.avg_price" class="meta">¥{{ p.avg_price }}/人</text>
            <text v-if="p.category" class="meta cat">{{ p.category }}</text>
          </view>
        </view>
      </view>
      <view v-if="!loading && searched && results.length === 0" class="empty">
        <text>{{ emptyHint }}</text>
      </view>
    </scroll-view>

    <view class="footer">
      <text class="foot-count">已选 {{ selected.size }} 家</text>
      <view class="foot-btns">
        <view class="fbtn ghost" @click="clearSel"><text>清空</text></view>
        <view class="fbtn primary" @click="submitBatch"><text>加入自己精选</text></view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { amapApi, restaurantApi } from '../../api'
import { getAmapCredentials, loadAmapScript } from '../../utils/amap-h5.js'
import { wgs84ToGcj02 } from '../../utils/geo-china.js'

/** H5=浏览器端；与微信小程序/App 区分。部分构建里平台名为 web 或 env 未注入，故加 uniPlatform 兜底。 */
function detectIsH5() {
  const p = import.meta.env.UNI_PLATFORM
  if (p === 'h5' || p === 'web') return true
  try {
    if (typeof uni !== 'undefined' && uni.getSystemInfoSync) {
      const { uniPlatform } = uni.getSystemInfoSync()
      if (uniPlatform === 'web' || uniPlatform === 'h5') return true
    }
  } catch (_) {
    /* ignore */
  }
  return false
}
const isH5 = detectIsH5()

const DEFAULT_LNG = 103.9986
const DEFAULT_LAT = 30.5865

const keyword = ref('')
const results = ref([])
const loading = ref(false)
const loadingText = ref('加载中…')
const searched = ref(false)
const selected = ref(new Set())
const nearbyRadius = ref(3000)
const radiusOptions = [1500, 3000, 5000]

/** 高德瓦片未就绪前避免白屏突兀，complete 后关闭 */
const mapLoading = ref(true)

let map = null
let mapResizeObserver = null
const markerInst = []
/** 关键词/周边搜索成功后，下一次同步标记时是否执行 setFitView */
const fitMarkersNext = ref(false)
/** 列表代数：新搜索递增，补图循环与写回仅作用于当前代 */
let listGenToken = 0
let mapPickHandler = null
let hotspotHandler = null
let pickClickTimer = null
/** 点击自定义标记时阻止触发地图拾取 */
let ignoreNextMapClick = false

function clearMarkers() {
  markerInst.forEach((m) => {
    m.setMap(null)
  })
  markerInst.length = 0
}

function unbindMapPick() {
  if (map && mapPickHandler) {
    map.off('click', mapPickHandler)
    mapPickHandler = null
  }
  if (map && hotspotHandler) {
    try {
      map.off('hotspotclick', hotspotHandler)
    } catch (_) {
      /* 部分版本无此事件 */
    }
    hotspotHandler = null
  }
  if (pickClickTimer) {
    clearTimeout(pickClickTimer)
    pickClickTimer = null
  }
}

function destroyMap() {
  unbindMapPick()
  if (mapResizeObserver) {
    mapResizeObserver.disconnect()
    mapResizeObserver = null
  }
  clearMarkers()
  if (map) {
    map.destroy()
    map = null
  }
  mapLoading.value = false
}

function scheduleMapResize() {
  if (!map || typeof map.resize !== 'function') return
  map.resize()
}

const emptyHint = ref('没有结果')

function getInitialCenter() {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      resolve([DEFAULT_LNG, DEFAULT_LAT])
      return
    }
    if (!window.isSecureContext) {
      resolve([DEFAULT_LNG, DEFAULT_LAT])
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const [lng, lat] = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude)
        resolve([lng, lat])
      },
      () => resolve([DEFAULT_LNG, DEFAULT_LAT]),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
    )
  })
}

/** 首屏建图用：缩短超时，与脚本并行，加快出现地图 */
function getInitialCenterFast() {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      resolve([DEFAULT_LNG, DEFAULT_LAT])
      return
    }
    if (!window.isSecureContext) {
      resolve([DEFAULT_LNG, DEFAULT_LAT])
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const [lng, lat] = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude)
        resolve([lng, lat])
      },
      () => resolve([DEFAULT_LNG, DEFAULT_LAT]),
      { enableHighAccuracy: false, timeout: 3200, maximumAge: 120000 }
    )
  })
}

async function initBaseMap() {
  if (!isH5) return
  mapLoading.value = true
  const { key, securityJsCode } = getAmapCredentials()
  if (!key || !securityJsCode) {
    mapLoading.value = false
    uni.showToast({
      title: '请在 manifest 配置高德 JS Key 与安全密钥',
      icon: 'none',
      duration: 3500,
    })
    return
  }
  const centerPromise = getInitialCenterFast()
  try {
    await loadAmapScript(key, securityJsCode)
  } catch {
    mapLoading.value = false
    uni.showToast({ title: '地图脚本加载失败', icon: 'none' })
    return
  }
  await nextTick()
  await new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  })
  const el =
    typeof document !== 'undefined' ? document.getElementById('batch-amap') : null
  if (el && el.offsetHeight < 16) {
    await new Promise((r) => setTimeout(r, 120))
  }
  const [lng, lat] = await centerPromise
  map = new window.AMap.Map('batch-amap', {
    zoom: 16,
    center: [lng, lat],
    viewMode: '2D',
  })
  scheduleMapResize()
  let mapLoadFinished = false
  const finishLoading = () => {
    if (mapLoadFinished) return
    mapLoadFinished = true
    mapLoading.value = false
    scheduleMapResize()
    ;[80, 200, 500].forEach((ms) => setTimeout(scheduleMapResize, ms))
  }
  map.on('complete', finishLoading)
  setTimeout(finishLoading, 1600)
  if (typeof ResizeObserver !== 'undefined' && el) {
    mapResizeObserver = new ResizeObserver(() => scheduleMapResize())
    mapResizeObserver.observe(el)
  }
  bindMapPick()
}

function bindMapPick() {
  if (!map || mapPickHandler) return
  hotspotHandler = (e) => {
    const name = e?.name ?? e?.data?.name
    const ll = e?.lnglat
    if (!name || !ll) return
    ignoreNextMapClick = true
    const lng = typeof ll.getLng === 'function' ? ll.getLng() : ll.lng
    const lat = typeof ll.getLat === 'function' ? ll.getLat() : ll.lat
    if (lng == null || lat == null) return
    void pickPoiFromHotspot(String(name), lng, lat)
  }
  try {
    map.on('hotspotclick', hotspotHandler)
  } catch (_) {
    hotspotHandler = null
  }
  mapPickHandler = (e) => {
    if (ignoreNextMapClick) {
      ignoreNextMapClick = false
      return
    }
    if (!e?.lnglat) return
    if (pickClickTimer) clearTimeout(pickClickTimer)
    pickClickTimer = setTimeout(() => {
      pickClickTimer = null
      const lng = e.lnglat.getLng()
      const lat = e.lnglat.getLat()
      pickPoiAt(lng, lat)
    }, 80)
  }
  map.on('click', mapPickHandler)
}

async function pickPoiFromHotspot(name, lng, lat) {
  try {
    const res = await amapApi.enrichPoi(name, lng, lat)
    if (res && res.code === 200 && res.data) {
      addOrTogglePoi(res.data)
      return
    }
  } catch (_) {
    /* fallback regeo */
  }
  await pickPoiAt(lng, lat)
}

function syncResultMarkers(options = {}) {
  const fit = options.fit === true
  if (!isH5 || !map) return
  clearMarkers()
  const list = results.value
  if (!list.length) return
  list.forEach((p, idx) => {
    if (p.longitude == null || p.latitude == null) return
    const sel = selected.value.has(idx)
    const m = new window.AMap.Marker({
      position: [p.longitude, p.latitude],
      map,
      label: {
        content: sel ? `✓${idx + 1}` : String(idx + 1),
        direction: 'top',
      },
    })
    m.on('click', () => {
      ignoreNextMapClick = true
      toggle(idx)
    })
    markerInst.push(m)
  })
  if (fit && markerInst.length) {
    map.setFitView(markerInst, false, [50, 50, 80, 380])
  }
}

function samePoiCoords(a, b) {
  return (
    a.name === b.name &&
    Math.abs((a.longitude || 0) - (b.longitude || 0)) < 1e-4 &&
    Math.abs((a.latitude || 0) - (b.latitude || 0)) < 1e-4
  )
}

function toggle(idx) {
  const s = new Set(selected.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  selected.value = s
}

function formatRequestErr(err) {
  if (err == null) return ''
  if (typeof err === 'string') return err
  if (typeof err.detail === 'string') return err.detail
  if (Array.isArray(err.detail) && err.detail[0]?.msg) return String(err.detail[0].msg)
  if (err.message) return String(err.message)
  return ''
}

async function pickBestRegeoCandidate(list) {
  if (!list?.length) return null
  const sorted = [...list].sort(
    (a, b) => (a.distance_from_click_m ?? 1e6) - (b.distance_from_click_m ?? 1e6),
  )
  const first = sorted[0]
  const second = sorted[1]
  const d0 = first.distance_from_click_m ?? 9999
  const d1 = second ? second.distance_from_click_m ?? 9999 : 1e6
  if (!second || d1 - d0 > 26) return first
  if (d0 > 95) return first
  const cluster = sorted
    .slice(0, 6)
    .filter((p) => (p.distance_from_click_m ?? 1e6) <= d0 + 24)
  if (cluster.length <= 1) return first
  return new Promise((resolve) => {
    uni.showActionSheet({
      itemList: cluster.map((p) => (p.name.length > 22 ? `${p.name.slice(0, 22)}…` : p.name)),
      success: (r) => resolve(cluster[r.tapIndex] || first),
      fail: () => resolve(first),
    })
  })
}

async function pickPoiAt(lng, lat) {
  try {
    const res = await amapApi.regeoPois(lng, lat, 120)
    if (res && res.code === 200 && res.data && res.data.length) {
      const chosen = await pickBestRegeoCandidate(res.data)
      if (chosen) addOrTogglePoi(chosen)
      return
    }
    const hint = res && res.message ? String(res.message) : ''
    uni.showToast({
      title: hint || '未识别到餐饮店，可放大地图或点「搜附近好店」',
      icon: 'none',
      duration: 2800,
    })
  } catch (err) {
    const raw = formatRequestErr(err)
    const is404 = raw.includes('Not Found') || raw.includes('404')
    uni.showToast({
      title: is404
        ? '接口 404：请重启后端；确保用 dev 地址访问且 vite 已配 /api 代理'
        : raw
          ? `拾取失败：${raw}`
          : '拾取失败：网络或后端不可用',
      icon: 'none',
      duration: is404 ? 4200 : 3200,
    })
  }
}

async function enrichRowImage(idx, gen = null) {
  const p = results.value[idx]
  if (!p?.name || p.longitude == null || p.latitude == null) return
  if (p.image_url && String(p.image_url).trim()) return
  const nameSnap = p.name
  try {
    const res = await amapApi.enrichPoi(p.name, p.longitude, p.latitude)
    if (gen != null && gen !== listGenToken) return
    if (res?.code !== 200 || !res.data) return
    const d = res.data
    const img = (d.image_url || '').replace(/^http:\/\//i, 'https://')
    if (!img && d.rating == null && d.avg_price == null) return
    const arr = [...results.value]
    const row = arr[idx]
    if (!row || row.name !== nameSnap) return
    const cur = { ...row }
    if (img) cur.image_url = img
    if (d.rating != null) cur.rating = d.rating
    if (d.avg_price != null) cur.avg_price = d.avg_price
    if (d.address && !cur.address) cur.address = d.address
    arr[idx] = cur
    if (gen != null && gen !== listGenToken) return
    results.value = arr
  } catch (_) {
    /* silent */
  }
}

/** 列表加载后对前若干条无图 POI 串行补图（限流，避免与新一代搜索打架） */
async function enrichListImages(gen) {
  const cap = 15
  const gapMs = 95
  for (let i = 0; i < cap; i++) {
    if (gen !== listGenToken) return
    if (i >= results.value.length) break
    const row = results.value[i]
    if (!row?.name || row.image_url) continue
    await enrichRowImage(i, gen)
    if (gen !== listGenToken) return
    await new Promise((r) => setTimeout(r, gapMs))
  }
}

function addOrTogglePoi(poi) {
  if (!poi?.name || poi.latitude == null || poi.longitude == null) return
  searched.value = true
  const idx = results.value.findIndex((x) => samePoiCoords(x, poi))
  if (idx >= 0) {
    const had = selected.value.has(idx)
    toggle(idx)
    uni.showToast({
      title: had ? `已取消「${poi.name}」` : `已选中「${poi.name}」`,
      icon: 'none',
    })
    return
  }
  const cleaned = { ...poi }
  delete cleaned.distance_from_click_m
  results.value = [...results.value, cleaned]
  const newIdx = results.value.length - 1
  const s = new Set(selected.value)
  s.add(newIdx)
  selected.value = s
  uni.showToast({ title: `已加入并选中「${poi.name}」`, icon: 'none' })
  void enrichRowImage(newIdx, null)
}

watch(results, () => {
  nextTick(() => {
    const fit = fitMarkersNext.value
    fitMarkersNext.value = false
    syncResultMarkers({ fit })
  })
})

watch(selected, () => {
  nextTick(() => syncResultMarkers({ fit: false }))
})

onMounted(() => {
  if (isH5) {
    initBaseMap()
  }
})

onUnmounted(() => {
  destroyMap()
})

const clearSel = () => {
  selected.value = new Set()
}

const recenterGps = async () => {
  if (!map) {
    uni.showToast({ title: '地图未就绪', icon: 'none' })
    return
  }
  uni.showLoading({ title: '定位中…', mask: true })
  try {
    const [lng, lat] = await getInitialCenter()
    map.setCenter([lng, lat])
    map.setZoom(16)
    uni.showToast({ title: '已移到当前位置', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

const doNearby = async () => {
  if (!map) {
    uni.showToast({ title: '地图未就绪', icon: 'none' })
    return
  }
  const c = map.getCenter()
  const lng = c.getLng()
  const lat = c.getLat()
  listGenToken += 1
  const gen = listGenToken
  loadingText.value = '搜附近餐厅…'
  loading.value = true
  searched.value = true
  results.value = []
  clearSel()
  emptyHint.value = '该范围内暂无餐饮 POI，可放大半径或拖动地图再试'
  try {
    const res = await amapApi.poiAround(lng, lat, nearbyRadius.value, 1)
    if (gen !== listGenToken) return
    if (res && res.code === 200 && res.data) {
      fitMarkersNext.value = true
      results.value = res.data.filter((x) => x.name && x.latitude != null && x.longitude != null)
      void enrichListImages(gen)
    } else {
      uni.showToast({ title: (res && res.message) || '周边检索失败', icon: 'none' })
    }
  } catch (_) {
    /* request */
  } finally {
    if (gen === listGenToken) loading.value = false
  }
}

const doSearch = async () => {
  const q = keyword.value.trim()
  if (!q) {
    uni.showToast({ title: '请输入关键词', icon: 'none' })
    return
  }
  listGenToken += 1
  const gen = listGenToken
  loadingText.value = '搜索中…'
  loading.value = true
  searched.value = true
  results.value = []
  clearSel()
  emptyHint.value = '没有结果，换个关键词试试'
  try {
    const res = await amapApi.poi(q, 1)
    if (gen !== listGenToken) return
    if (res && res.code === 200 && res.data) {
      fitMarkersNext.value = true
      results.value = res.data.filter((x) => x.name && x.latitude != null && x.longitude != null)
      void enrichListImages(gen)
    } else {
      uni.showToast({ title: (res && res.message) || '搜索失败', icon: 'none' })
    }
  } catch (_) {
    /* request */
  } finally {
    if (gen === listGenToken) loading.value = false
  }
}

const poiToItem = (p) => ({
  name: p.name,
  address: p.address || '',
  latitude: p.latitude,
  longitude: p.longitude,
  avg_price: p.avg_price != null ? p.avg_price : undefined,
  category: p.category || '餐饮服务',
  tags: p.tag || '',
  image_url: (p.image_url || '').replace(/^http:\/\//i, 'https://'),
  rating: p.rating != null ? p.rating : undefined,
  source: 'amap',
  boards: 'my_pick',
})

const submitBatch = async () => {
  if (selected.value.size === 0) {
    uni.showToast({ title: '请先勾选店铺', icon: 'none' })
    return
  }
  const items = [...selected.value]
    .sort((a, b) => a - b)
    .map((i) => poiToItem(results.value[i]))
  uni.showLoading({ title: '添加中…', mask: true })
  try {
    const res = await restaurantApi.batch(items)
    uni.showToast({
      title: `成功 ${res.created} 家，跳过 ${res.skipped} 家`,
      icon: 'none',
      duration: 2500,
    })
    setTimeout(() => uni.navigateBack(), 600)
  } catch (_) {
    /* handled */
  } finally {
    uni.hideLoading()
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx 24rpx 200rpx;
  background: #f7f6f5;
  box-sizing: border-box;
}
.hint {
  display: block;
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.55;
  margin-bottom: 20rpx;
}
.nh5-tip {
  padding: 20rpx;
  background: #fffbeb;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
  font-size: 24rpx;
  color: #92400e;
  line-height: 1.45;
}
.search-row {
  display: flex;
  flex-direction: row;
  gap: 16rpx;
  margin-bottom: 16rpx;
  align-items: center;
}
.search-input {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 48rpx;
  padding: 22rpx 28rpx;
  font-size: 28rpx;
  border: 1rpx solid #e7e5e4;
}
.search-btn {
  flex-shrink: 0;
  padding: 22rpx 36rpx;
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  border-radius: 9999rpx;
}
.search-btn-t {
  font-size: 28rpx;
  font-weight: 700;
  color: #fff;
}

.nearby-bar {
  margin-bottom: 16rpx;
}
.radius-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
  flex-wrap: wrap;
}
.radius-label {
  font-size: 24rpx;
  color: #57534e;
  font-weight: 600;
}
.radius-chip {
  padding: 10rpx 22rpx;
  border-radius: 9999rpx;
  background: #fff;
  border: 1rpx solid #e7e5e4;
}
.radius-chip text {
  font-size: 22rpx;
  color: #57534e;
}
.radius-on {
  background: #1c1917;
  border-color: #1c1917;
}
.radius-on text {
  color: #fff;
  font-weight: 700;
}
.nearby-actions {
  display: flex;
  flex-direction: row;
  gap: 12rpx;
}
.nbtn {
  flex: 1;
  padding: 20rpx 16rpx;
  border-radius: 9999rpx;
  text-align: center;
}
.nbtn.outline {
  background: #fff;
  border: 2rpx solid #9b3f00;
}
.nbtn.outline .nbtn-t {
  color: #9b3f00;
}
.nbtn.primary {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
}
.nbtn.primary .nbtn-t {
  color: #fff;
}
.nbtn-t {
  font-size: 26rpx;
  font-weight: 700;
}

.map-wrap {
  position: relative;
  margin-bottom: 16rpx;
}
.map-stage {
  position: relative;
  width: 100%;
  border-radius: 24rpx;
  overflow: hidden;
}
.batch-amap {
  width: 100%;
  height: 52vh;
  min-height: 300px;
  max-height: 560px;
  background: #dcdad6;
  overflow: hidden;
}
.map-loading-mask {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 8;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(245, 244, 242, 0.92);
  pointer-events: none;
}
.map-loading-text {
  font-size: 28rpx;
  color: #57534e;
  font-weight: 600;
}
.map-cross {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 48rpx;
  height: 48rpx;
  margin-left: -24rpx;
  margin-top: -24rpx;
  pointer-events: none;
  z-index: 12;
}
.cross-v {
  position: absolute;
  left: 50%;
  top: 0;
  width: 4rpx;
  height: 100%;
  margin-left: -2rpx;
  background: #9b3f00;
  border-radius: 2rpx;
  box-shadow: 0 0 6rpx #fff;
}
.cross-h {
  position: absolute;
  top: 50%;
  left: 0;
  height: 4rpx;
  width: 100%;
  margin-top: -2rpx;
  background: #9b3f00;
  border-radius: 2rpx;
  box-shadow: 0 0 6rpx #fff;
}
.cross-dot {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 16rpx;
  height: 16rpx;
  margin: -8rpx 0 0 -8rpx;
  background: #ff7a2c;
  border-radius: 50%;
  border: 3rpx solid #fff;
  box-sizing: border-box;
}
.map-tip {
  display: block;
  font-size: 22rpx;
  color: #78716c;
  margin-top: 8rpx;
  text-align: center;
}
.steps-bar {
  margin-top: 16rpx;
  padding: 16rpx 20rpx;
  background: #fff7ed;
  border-radius: 16rpx;
  border: 1rpx solid #fed7aa;
}
.steps-text {
  font-size: 24rpx;
  color: #9a3412;
  line-height: 1.5;
}

.loading {
  padding: 40rpx;
  text-align: center;
  color: #a8a29e;
  font-size: 28rpx;
}
/* 勿用 calc(100vh - 大量rpx)：宽屏下 rpx 换算过大，max-height 会变负，列表被压没 */
.list {
  height: 50vh;
  min-height: 280px;
  max-height: 560px;
}
.list-with-map {
  height: 36vh;
  min-height: 260px;
  max-height: 420px;
}
.list-placeholder {
  padding: 32rpx 24rpx 24rpx;
  margin-bottom: 8rpx;
}
.list-placeholder-t {
  font-size: 26rpx;
  color: #78716c;
  line-height: 1.55;
}
.idx-badge {
  display: block;
  font-size: 22rpx;
  font-weight: 800;
  color: #9b3f00;
  text-align: center;
  margin-bottom: 4rpx;
}
.row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 16rpx;
  padding: 20rpx;
  margin-bottom: 16rpx;
  background: #fff;
  border-radius: 24rpx;
  border: 2rpx solid transparent;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
}
.row-on {
  border-color: #9b3f00;
  background: #fffaf5;
}
.row-check {
  width: 56rpx;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  display: flex;
}
.check-icon {
  font-size: 36rpx;
  color: #9b3f00;
}
.row-img {
  width: 140rpx;
  height: 140rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
}
.row-img-ph {
  background: linear-gradient(135deg, #d6d3d1, #a8a29e);
}
.row-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.row-name {
  font-size: 30rpx;
  font-weight: 700;
  color: #1c1917;
}
.row-addr {
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.4;
}
.row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.meta {
  font-size: 22rpx;
  color: #c2410c;
  font-weight: 600;
}
.meta.cat {
  color: #57534e;
  font-weight: 500;
}
.empty {
  padding: 80rpx 24rpx;
  text-align: center;
  color: #a8a29e;
  font-size: 28rpx;
}
.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20rpx 32rpx calc(20rpx + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1rpx solid #e7e5e4;
  box-shadow: 0 -8rpx 24rpx rgba(0, 0, 0, 0.06);
}
.foot-count {
  display: block;
  font-size: 26rpx;
  color: #57534e;
  margin-bottom: 16rpx;
  text-align: center;
}
.foot-btns {
  display: flex;
  flex-direction: row;
  gap: 20rpx;
}
.fbtn {
  flex: 1;
  padding: 24rpx;
  border-radius: 9999rpx;
  text-align: center;
}
.fbtn text {
  font-size: 28rpx;
  font-weight: 700;
}
.fbtn.ghost {
  background: #e7e5e4;
  color: #44403c;
}
.fbtn.primary {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
}
.fbtn.primary text {
  color: #fff;
}
</style>

<template>
  <view class="page">
    <view class="hero-section">
      <text class="hero-title">今天吃啥</text>
      <text class="hero-subtitle">附近有什么好店 · 随手挑几家进精选 · 再抽签</text>
    </view>

    <view class="loc-bar" v-if="hasUserCoords && selectedDistance">
      <text class="loc-bar-main">📍 {{ locationShort }} · 周围 {{ selectedDistance }}km</text>
      <text class="loc-bar-more" @click="showingFilters = true">位置与筛选</text>
    </view>
    <view class="loc-bar loc-bar-warn" v-else-if="selectedDistance && !hasUserCoords">
      <text class="loc-bar-main">需要位置才能按距离推荐</text>
      <text class="loc-bar-more" @click="showingFilters = true">去设置</text>
    </view>

    <view class="discover-wrap">
      <view v-if="railsLoading" class="rails-loading">
        <text class="rails-loading-t">加载附近推荐…</text>
      </view>
      <template v-else>
        <view v-for="block in discoverBlocks" :key="block.key" class="discover-block">
          <view class="discover-head">
            <text class="discover-title">{{ block.title }}</text>
            <text class="discover-sub">{{ block.sub }}</text>
          </view>
          <scroll-view v-if="block.list.length" class="trending-scroll" scroll-x :show-scrollbar="false">
            <view class="trending-row">
              <view
                v-for="r in block.list"
                :key="block.key + '-' + r.id"
                class="trending-card trending-card-rail"
              >
                <view class="trending-card-tap" @click="goDetail(r)">
                  <view class="trending-img-wrap">
                    <image v-if="r.image_url" class="trending-img" :src="r.image_url" mode="aspectFill" />
                    <view v-else class="trending-img-placeholder"></view>
                  </view>
                  <text class="trending-name">{{ r.name }}</text>
                  <view class="trending-meta">
                    <text class="trending-rating" v-if="r.rating">{{ r.rating }}★</text>
                    <text class="trending-dot" v-if="r.rating && r.distance_km != null">·</text>
                    <text class="trending-distance" v-if="r.distance_km != null">{{ formatKm(r.distance_km) }}</text>
                    <text class="trending-category" v-if="r.distance_km == null && r.category">{{ r.category }}</text>
                  </view>
                </view>
                <view
                  :class="['rail-pick', isMyPick(r) ? 'rail-pick-on' : '']"
                  @click.stop="addToMyPick(r)"
                >
                  <text class="rail-pick-t">{{ isMyPick(r) ? '已在精选' : '加入精选' }}</text>
                </view>
              </view>
            </view>
          </scroll-view>
          <view v-else class="rail-empty">
            <text class="rail-empty-t">{{ block.emptyTip }}</text>
          </view>
        </view>
      </template>
    </view>

    <!-- Card Stack — Figma Interactive Carousel -->
    <view class="card-stack" v-if="picked">
      <view class="stack-bg stack-bg-back"></view>
      <view class="stack-bg stack-bg-mid"></view>
      <view class="active-card" @click="goDetail(picked)">
        <view class="active-card-img-wrap">
          <image v-if="picked.image_url" class="active-card-img" :src="picked.image_url" mode="aspectFill" />
          <view v-else class="active-card-img-placeholder">
            <text class="placeholder-icon">🍽</text>
          </view>
          <view class="top-match-badge">
            <text class="top-match-text">抽中这家</text>
          </view>
        </view>
        <view class="active-card-info">
          <view class="active-card-row">
            <text class="active-card-name">{{ picked.name }}</text>
            <text class="active-card-price">{{ priceTierRangeLabel(picked.price_tier) }}</text>
          </view>
          <text class="active-card-desc">{{ picked.category || '美味餐厅' }}{{ picked.address ? ' · ' + picked.address : '' }}</text>
          <view class="source-pills">
            <view class="source-pill" v-if="picked.source && picked.source !== 'manual'">
              <text class="source-pill-text">{{ { douyin: '抖音', amap: '高德', dianping: '点评' }[picked.source] || picked.source }}</text>
            </view>
            <view class="source-pill" v-if="picked.rating">
              <text class="source-pill-text">{{ picked.rating }}★</text>
            </view>
            <view class="source-pill" v-if="picked.avg_price">
              <text class="source-pill-text">¥{{ picked.avg_price }}/人</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Empty Card Stack -->
    <view class="card-stack" v-if="!picked">
      <view class="stack-bg stack-bg-back"></view>
      <view class="stack-bg stack-bg-mid"></view>
      <view class="active-card active-card-empty">
        <text class="empty-stack-icon">🎲</text>
        <text class="empty-stack-title">还没抽签</text>
        <text class="empty-stack-desc">点下面「抽一家」试试</text>
      </view>
    </view>

    <!-- CTA -->
    <view class="cta-wrap">
      <view class="btn-cta" @click="pickRandom">
        <text class="btn-cta-text">抽一家</text>
      </view>
    </view>

    <view class="secondary-row">
      <view class="pill-btn" @click="pickRandom" v-if="picked">
        <text class="pill-btn-text">再抽</text>
      </view>
      <view class="pill-btn" @click="showingFilters = !showingFilters">
        <text class="pill-btn-text">{{ showingFilters ? '收起筛选' : '人均·距离·分类' }}</text>
      </view>
      <view class="pill-btn pill-btn-accent" v-if="picked" @click="goEat(picked)">
        <text class="pill-btn-accent-text">就这家了</text>
      </view>
    </view>

    <!-- Filters Panel (collapsible) -->
    <view class="filters-panel" v-if="showingFilters">
      <view class="filter-section">
        <text class="filter-label">价格（人均参考，元）</text>
        <view class="chip-row">
          <view
            v-for="tier in tiers"
            :key="tier.value"
            :class="['chip', 'chip-price', selectedTier === tier.value ? 'chip-active' : '']"
            @click="selectedTier = selectedTier === tier.value ? '' : tier.value"
          >
            <text class="chip-price-main">{{ tier.label }}</text>
            <text v-if="tier.sub" class="chip-price-sub">{{ tier.sub }}</text>
          </view>
        </view>
      </view>
      <view class="filter-divider"></view>
      <view class="filter-section">
        <text class="filter-label">距离</text>
        <view class="chip-row">
          <view
            v-for="d in distances"
            :key="d.value"
            :class="['chip', selectedDistance === d.value ? 'chip-active' : '']"
            @click="selectedDistance = selectedDistance === d.value ? '' : d.value"
          >{{ d.label }}</view>
        </view>
      </view>
      <view class="filter-section loc-section">
        <text class="filter-label">我的位置</text>
        <text class="loc-hint" v-if="!hasUserCoords && !selectedDistance">
          可先输入地址或选参考点；选择上方「1km / 3km…」后，将按该位置筛选距离。
        </text>
        <text class="loc-hint loc-hint-warn" v-else-if="!hasUserCoords && selectedDistance">
          已选距离筛选：请完成定位、输入地址解析，或使用成信大参考点。
        </text>
        <view v-if="hasUserCoords" class="loc-settled">
          <text class="loc-settled-text">{{ locationLabel }}</text>
          <text class="loc-reset" @click="clearManualLocation">更改</text>
        </view>
        <view v-else class="loc-setup">
          <view class="loc-actions">
            <view class="loc-pill" @click="onTapGetGps"><text class="loc-pill-text">当前定位</text></view>
            <view class="loc-pill" @click="onTapChooseMap"><text class="loc-pill-text">地图选点</text></view>
          </view>
          <view class="loc-geocode">
            <view class="filter-input-shell loc-geocode-input-shell">
              <input
                class="filter-input"
                v-model="manualAddress"
                placeholder="输入地址：成都信息工程大学、小区、路名…"
                confirm-type="search"
                @confirm="onGeocodeAddress"
              />
            </view>
            <view class="loc-pill loc-pill-primary" @click="onGeocodeAddress">
              <text class="loc-pill-text">解析地址</text>
            </view>
          </view>
          <text class="loc-fallback" @click="applyChengduFallback(false)">暂不定位，用成都信息工程大学参考点</text>
        </view>
      </view>
      <view class="filter-divider"></view>
      <view class="filter-section filter-section-input">
        <text class="filter-label">分类</text>
        <view class="filter-input-shell">
          <input class="filter-input" v-model="category" placeholder="火锅、川菜、烧烤..." />
        </view>
      </view>
    </view>

  </view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { restaurantApi, amapApi } from '../../api'
import { wgs84ToGcj02 } from '../../utils/geo-china'

/** 与后端 PriceTierEnum 一致：0-10 / 10-20 / 20-50 / 50-100 / 100+ */
const tiers = [
  { label: '0–10', sub: '元', value: '0-10' },
  { label: '10–20', sub: '元', value: '10-20' },
  { label: '20–50', sub: '元', value: '20-50' },
  { label: '50–100', sub: '元', value: '50-100' },
  { label: '100+', sub: '元', value: '100+' },
]
const distances = [
  { label: '全城', value: '' },
  { label: '1km', value: '1' },
  { label: '3km', value: '3' },
  { label: '5km', value: '5' },
  { label: '8km', value: '8' },
  { label: '10km', value: '10' },
  { label: '20km', value: '20' },
]

const selectedTier = ref('')
/** 默认 8km：进入页即可看到「附近」三类推荐，减少空手状态 */
const selectedDistance = ref('8')
const category = ref('')
const picked = ref(null)
const railHigh = ref([])
const railViral = ref([])
const railMust = ref([])
const railsLoading = ref(false)
const showingFilters = ref(false)
/** 首次进入用参考点拉推荐，避免列表全空 */
const locationBootstrapped = ref(false)
const userLat = ref(null)
const userLng = ref(null)
const locationLabel = ref('')
const manualAddress = ref('')

/** 成都信息工程大学航空港校区参考点（GCJ-02） */
const FALLBACK_LAT = 30.5865
const FALLBACK_LNG = 103.9986

/** 勿用 Number(x)：Number(null)===0 会把「未设置」误判成有效坐标 (0,0) */
const hasUserCoords = computed(() => {
  const rawLa = userLat.value
  const rawLn = userLng.value
  if (rawLa == null || rawLn == null || rawLa === '' || rawLn === '') return false
  const la = Number(rawLa)
  const ln = Number(rawLn)
  return Number.isFinite(la) && Number.isFinite(ln)
})

/** 卡片上展示具体人均区间 */
const priceTierRangeLabel = (tier) => {
  if (!tier) return '人均未选'
  const map = {
    '0-10': '人均0-10元',
    '10-20': '人均10-20元',
    '20-50': '人均20-50元',
    '50-100': '人均50-100元',
    '100+': '人均100元以上',
  }
  return map[tier] || `人均${tier}元`
}

const locationShort = computed(() => {
  const s = (locationLabel.value || '').trim()
  if (!s) return '当前位置'
  return s.length > 20 ? `${s.slice(0, 20)}…` : s
})

function formatKm(km) {
  const n = Number(km)
  if (!Number.isFinite(n)) return ''
  if (n < 1) return `距你${Math.round(n * 1000)}m`
  return `距你${n.toFixed(n >= 10 ? 0 : 1)}km`
}

function boardsTokenSet(boards) {
  return new Set(
    String(boards || '')
      .split(';')
      .map((x) => x.trim())
      .filter(Boolean),
  )
}

function boardsJoin(tokens) {
  return [...tokens].sort().join(';')
}

function isMyPick(r) {
  return boardsTokenSet(r.boards).has('my_pick')
}

async function addToMyPick(r) {
  if (!r?.id) return
  const b = boardsTokenSet(r.boards)
  if (b.has('my_pick')) {
    uni.showToast({ title: '已在精选里', icon: 'none' })
    return
  }
  b.add('my_pick')
  const next = boardsJoin(b)
  try {
    await restaurantApi.update(r.id, { boards: next }, { silent: true })
    r.boards = next
    uni.showToast({ title: '已加入我的精选', icon: 'success' })
  } catch (_) {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

const discoverBlocks = computed(() => [
  {
    key: 'worth',
    title: '附近值得去',
    sub: '高分优先 · 按距离',
    list: railHigh.value,
    emptyTip: '这个范围内暂无高分店，可扩大距离或去「发现美食」看看',
  },
  {
    key: 'viral',
    title: '网红打卡',
    sub: '同款向收录',
    list: railViral.value,
    emptyTip: '暂无网红向店铺，可在发现页导入抖音笔记',
  },
  {
    key: 'must',
    title: '必吃榜向',
    sub: '含「必吃」标签或关键词',
    list: railMust.value,
    emptyTip: '附近暂无带「必吃」标签的店，可在发现里收录或扩大范围',
  },
])

/** @returns {Promise<{ ok: boolean, reason?: string }>} */
const getLocation = () => {
  return new Promise((resolve) => {
    // #ifdef H5
    if (typeof window !== 'undefined' && !window.isSecureContext) {
      resolve({ ok: false, reason: 'insecure' })
      return
    }
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      resolve({ ok: false, reason: 'no-api' })
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const [gcjLng, gcjLat] = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude)
        userLat.value = gcjLat
        userLng.value = gcjLng
        locationLabel.value = '当前定位（GPS）'
        resolve({ ok: true })
      },
      (err) => {
        let reason = 'unknown'
        if (err && err.code === 1) reason = 'denied'
        else if (err && err.code === 2) reason = 'unavailable'
        else if (err && err.code === 3) reason = 'timeout'
        resolve({ ok: false, reason })
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
    )
    // #endif
    // #ifndef H5
    uni.getLocation({
      type: 'gcj02',
      // #ifdef APP-PLUS
      isHighAccuracy: true,
      highAccuracyExpireTime: 5000,
      // #endif
      success: (res) => {
        userLat.value = res.latitude
        userLng.value = res.longitude
        locationLabel.value = '当前定位（GPS）'
        resolve({ ok: true })
      },
      fail: (err) => {
        const msg = (err && err.errMsg) || ''
        resolve({ ok: false, reason: msg || 'uni-fail' })
      },
    })
    // #endif
  })
}

function geoFailToast(reason) {
  const map = {
    insecure:
      '请用 http://localhost:5177 或 https 访问（局域网 IP + http 时浏览器禁止定位）',
    'no-api': '当前浏览器不支持定位',
    denied: '定位被拒绝：点击地址栏锁形图标 → 允许位置',
    timeout: '定位超时：请打开系统定位或到窗边重试',
    unavailable: '暂时无法获取位置，请用输入地址或地图选点',
    unknown: '定位失败，请用输入地址或地图选点',
    'uni-fail': '定位失败，请检查权限或改用输入地址',
  }
  let text = map[reason] || map.unknown
  if (reason && reason.includes && (reason.includes('auth deny') || reason.includes('PERMISSION_DENIED'))) {
    text = map.denied
  }
  uni.showToast({ title: text, icon: 'none', duration: 4000 })
}

/**
 * 非 H5：从「全城」首次选距离时尝试一次 GPS。
 * H5：浏览器只允许在用户点击等手势里请求定位，自动调用不会弹授权且常失败，故不自动请求。
 */
const initLocationForDistance = async () => {
  if (!selectedDistance.value) return
  // #ifdef H5
  return
  // #endif
  // #ifndef H5
  const loc = await getLocation()
  if (!loc.ok) {
    userLat.value = null
    userLng.value = null
    locationLabel.value = ''
  }
  // #endif
}

/** 不用 async，整段在点击同步栈里挂上 getCurrentPosition，避免丢浏览器「用户手势」 */
const onTapGetGps = () => {
  const locPromise = getLocation()
  uni.showLoading({ title: '定位中…', mask: true })
  locPromise
    .then((loc) => {
      if (loc.ok) {
        uni.showToast({ title: '已获取定位', icon: 'success' })
        return fetchDiscoveryRails()
      }
      geoFailToast(loc.reason)
    })
    .finally(() => {
      uni.hideLoading()
    })
}

const applyMapPick = (res) => {
  userLat.value = res.latitude
  userLng.value = res.longitude
  const name = res.name || ''
  const addr = res.address || ''
  locationLabel.value = name ? `${name}（地图）` : `${addr || '所选位置'}（地图）`
  uni.showToast({ title: '已选位置', icon: 'success' })
  void fetchDiscoveryRails()
}

const onTapChooseMap = () => {
  // #ifdef H5
  uni.navigateTo({
    url: '/pages/pick/map-picker',
    events: {
      pickLocation(data) {
        if (data && data.latitude != null && data.longitude != null) {
          applyMapPick(data)
        }
      },
    },
  })
  // #endif
  // #ifndef H5
  uni.chooseLocation({
    success: (res) => applyMapPick(res),
    fail: () => {
      uni.showToast({ title: '未选择地点或选点失败', icon: 'none' })
    },
  })
  // #endif
}

const onGeocodeAddress = async () => {
  const q = manualAddress.value.trim()
  if (!q) {
    uni.showToast({ title: '请先输入地点', icon: 'none' })
    return
  }
  uni.showLoading({ title: '解析中…', mask: true })
  try {
    const res = await amapApi.geocode(q)
    if (res && res.code === 200 && res.data) {
      userLat.value = res.data.latitude
      userLng.value = res.data.longitude
      locationLabel.value = (res.data.formatted_address || q) + '（地址）'
      manualAddress.value = ''
      uni.showToast({ title: '已解析位置', icon: 'success' })
      await fetchDiscoveryRails()
    } else {
      uni.showToast({ title: (res && res.message) || '未找到该地址', icon: 'none' })
    }
  } catch (_) {
    /* request 已 toast */
  } finally {
    uni.hideLoading()
  }
}

const applyChengduFallback = (silent = false) => {
  userLat.value = FALLBACK_LAT
  userLng.value = FALLBACK_LNG
  locationLabel.value = '成都信息工程大学（参考点）'
  if (!silent) {
    uni.showToast({ title: '已使用成信大参考点', icon: 'none' })
  }
  void fetchDiscoveryRails()
}

const clearManualLocation = async () => {
  userLat.value = null
  userLng.value = null
  locationLabel.value = ''
  manualAddress.value = ''
  if (selectedDistance.value) {
    await initLocationForDistance()
  }
  void fetchDiscoveryRails()
}

const buildParams = () => {
  const params = {}
  if (selectedTier.value) params.price_tier = selectedTier.value
  if (category.value) params.category = category.value
  if (selectedDistance.value && hasUserCoords.value) {
    params.user_lat = Number(userLat.value)
    params.user_lng = Number(userLng.value)
    params.max_distance_km = selectedDistance.value
  }
  return params
}

const pickRandom = async () => {
  if (selectedDistance.value && !hasUserCoords.value) {
    uni.showToast({ title: '请先设置「我的位置」', icon: 'none' })
    return
  }
  try {
    picked.value = await restaurantApi.random(buildParams())
  } catch (e) {
    if (e && e.detail) {
      uni.showToast({ title: e.detail, icon: 'none' })
    }
  }
}

const fetchDiscoveryRails = async () => {
  railsLoading.value = true
  try {
    if (!hasUserCoords.value || !selectedDistance.value) {
      railHigh.value = []
      railViral.value = []
      railMust.value = []
      return
    }
    const base = {
      user_lat: Number(userLat.value),
      user_lng: Number(userLng.value),
      max_distance_km: Number(selectedDistance.value),
      sort_by: 'distance',
      limit: 18,
    }
    const tier = selectedTier.value
    const cat = (category.value || '').trim()
    const extra = {}
    if (tier) extra.price_tier = tier
    if (cat) extra.category = cat
    const [high, viral, must] = await Promise.all([
      restaurantApi.list({ ...base, ...extra, board: 'high_score' }),
      restaurantApi.list({ ...base, ...extra, board: 'viral' }),
      restaurantApi.list({ ...base, ...extra, keyword: '必吃' }),
    ])
    railHigh.value = (high || []).slice(0, 12)
    railViral.value = (viral || []).slice(0, 12)
    railMust.value = (must || []).slice(0, 12)
  } catch (_) {
    railHigh.value = []
    railViral.value = []
    railMust.value = []
  } finally {
    railsLoading.value = false
  }
}

const goDetail = (restaurant) => {
  uni.navigateTo({
    url: `/pages/detail/detail?id=${restaurant.id}`
  })
}

const goEat = (restaurant) => {
  uni.navigateTo({
    url: `/pages/records/add?restaurant_id=${restaurant.id}&restaurant_name=${encodeURIComponent(restaurant.name)}`
  })
}

onShow(async () => {
  if (!locationBootstrapped.value) {
    locationBootstrapped.value = true
    if (userLat.value == null || userLng.value == null || userLat.value === '' || userLng.value === '') {
      applyChengduFallback(true)
    }
  }
  if (selectedDistance.value && !hasUserCoords.value) {
    await initLocationForDistance()
  }
  await fetchDiscoveryRails()
})

watch([selectedTier, selectedDistance, category], async (_n, oldVals) => {
  const prevDist = oldVals && oldVals.length > 1 ? oldVals[1] : ''
  const dist = selectedDistance.value
  if (!dist) {
    userLat.value = null
    userLng.value = null
    locationLabel.value = ''
    manualAddress.value = ''
  } else if (!prevDist && dist) {
    await initLocationForDistance()
  }
  await fetchDiscoveryRails()
})
</script>

<style scoped>
.page {
  padding: 40rpx 32rpx 120rpx;
  min-height: 100vh;
  background: #f7f6f5;
}

/* ---- Hero Section ---- */
.hero-section { margin-bottom: 40rpx; }
.hero-title {
  display: block; font-size: 84rpx; font-weight: 900; color: #9b3f00;
  letter-spacing: -2rpx; line-height: 1.05;
}
.hero-subtitle {
  display: block; font-size: 30rpx; font-weight: 500; color: #a8a29e;
  margin-top: 4rpx; letter-spacing: 1rpx;
}
.loc-bar {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 20rpx 24rpx;
  background: #fff;
  border-radius: 40rpx;
  margin-bottom: 28rpx;
  border: 1rpx solid #e7e5e4;
  box-shadow: 0 8rpx 20rpx rgba(0, 0, 0, 0.04);
}
.loc-bar-warn {
  border-color: #fcd34d;
  background: #fffbeb;
}
.loc-bar-main {
  flex: 1;
  font-size: 26rpx;
  color: #44403c;
  line-height: 1.4;
  min-width: 0;
}
.loc-bar-more {
  font-size: 24rpx;
  font-weight: 700;
  color: #9b3f00;
  flex-shrink: 0;
}

.discover-wrap {
  margin-bottom: 36rpx;
}
.rails-loading {
  padding: 48rpx 0;
  text-align: center;
}
.rails-loading-t {
  font-size: 26rpx;
  color: #a8a29e;
}
.discover-block {
  margin-bottom: 36rpx;
}
.discover-head {
  margin-bottom: 16rpx;
  padding-left: 4rpx;
}
.discover-title {
  display: block;
  font-size: 32rpx;
  font-weight: 800;
  color: #1c1917;
  letter-spacing: -0.5rpx;
}
.discover-sub {
  display: block;
  font-size: 22rpx;
  color: #a8a29e;
  margin-top: 6rpx;
}
.rail-empty {
  padding: 28rpx 24rpx;
  background: #fafaf9;
  border-radius: 28rpx;
  border: 1rpx dashed #e7e5e4;
}
.rail-empty-t {
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.5;
}
.trending-card-rail {
  display: flex;
  flex-direction: column;
  width: 260rpx;
  padding-bottom: 12rpx;
}
.trending-card-tap {
  flex: 1;
  min-height: 0;
}
.rail-pick {
  margin: 8rpx 16rpx 0;
  padding: 12rpx 0;
  border-radius: 9999rpx;
  background: #f5f5f4;
  border: 1rpx solid #e7e5e4;
  text-align: center;
}
.rail-pick:active {
  opacity: 0.9;
}
.rail-pick-on {
  background: rgba(155, 63, 0, 0.12);
  border-color: rgba(155, 63, 0, 0.35);
}
.rail-pick-t {
  font-size: 22rpx;
  font-weight: 700;
  color: #9b3f00;
}

/* ---- Card Stack ---- */
.card-stack {
  position: relative;
  z-index: 0;
  margin-bottom: 32rpx;
  padding: 20rpx 0 10rpx;
  /* rotate 后的装饰层会超出盒子，可能挡住下方筛选区点击 */
  overflow: hidden;
}
.stack-bg {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  height: 90%;
  border-radius: 96rpx;
  pointer-events: none;
}
.stack-bg-back {
  background: #e2e2e1; opacity: 0.5;
  top: 40rpx;
  transform: rotate(-4deg);
}
.stack-bg-mid {
  background: #e8e8e7; opacity: 0.8;
  top: 20rpx;
  transform: rotate(2deg);
}
.active-card {
  position: relative; z-index: 2;
  background: #ffffff; border-radius: 96rpx;
  box-shadow: 0 24rpx 64rpx rgba(0,0,0,0.06);
  overflow: hidden;
}
.active-card-empty {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 100rpx 40rpx;
}
.empty-stack-icon { font-size: 80rpx; display: block; margin-bottom: 16rpx; }
.empty-stack-title {
  font-size: 32rpx; font-weight: 700; color: var(--color-text);
  display: block; margin-bottom: 8rpx;
}
.empty-stack-desc {
  font-size: 26rpx; color: #a8a29e; display: block;
}

/* Active card content */
.active-card-img-wrap {
  position: relative; height: 560rpx; margin: 24rpx 24rpx 0;
  border-radius: 80rpx; overflow: hidden;
}
.active-card-img { width: 100%; height: 100%; }
.active-card-img-placeholder {
  width: 100%; height: 100%;
  background: linear-gradient(135deg, #44403c, #78716c);
  display: flex; align-items: center; justify-content: center;
}
.placeholder-icon { font-size: 80rpx; }
.top-match-badge {
  position: absolute; top: 24rpx; left: 24rpx;
  background: rgba(155,63,0,0.9);
  border-radius: 9999rpx; padding: 10rpx 28rpx;
}
.top-match-text { font-size: 24rpx; font-weight: 700; color: #fff; }

.active-card-info { padding: 28rpx 36rpx 32rpx; }
.active-card-row {
  display: flex; justify-content: space-between;
  align-items: baseline; margin-bottom: 8rpx;
}
.active-card-name {
  font-size: 66rpx; font-weight: 900; color: #1c1917;
  letter-spacing: -2rpx; line-height: 1.1;
  flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.active-card-price {
  font-size: 44rpx; color: #a8a29e; font-weight: 500;
  flex-shrink: 0; margin-left: 16rpx;
}
.active-card-desc {
  display: block; font-size: 26rpx; color: #78716c;
  line-height: 1.5; margin-bottom: 20rpx;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.source-pills { display: flex; flex-wrap: wrap; gap: 12rpx; }
.source-pill {
  padding: 8rpx 24rpx; border-radius: 9999rpx;
  background: #f5f5f4; border: 1rpx solid #e7e5e4;
}
.source-pill-text { font-size: 24rpx; font-weight: 500; color: #57534e; }

/* ---- CTA Button ---- */
.cta-wrap { margin-bottom: 24rpx; }
.btn-cta {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  border-radius: 9999rpx; padding: 32rpx 80rpx;
  text-align: center;
  box-shadow: 0 24rpx 96rpx rgba(155,63,0,0.3);
}
.btn-cta:active { opacity: 0.92; transform: scale(0.98); }
.btn-cta-text { font-size: 36rpx; font-weight: 800; color: #fff; }

/* ---- Secondary Actions ---- */
.secondary-row {
  display: flex; justify-content: center;
  gap: 16rpx; margin-bottom: 48rpx;
  flex-wrap: wrap;
}
.pill-btn {
  background: #e2e2e1; border-radius: 9999rpx;
  padding: 18rpx 44rpx;
}
.pill-btn:active { background: #d6d3d1; }
.pill-btn-text { font-size: 26rpx; font-weight: 600; color: #44403c; }
.pill-btn-accent {
  background: var(--color-accent-orange-bg);
}
.pill-btn-accent-text {
  font-size: 26rpx; font-weight: 700; color: #9a3412;
}

/* ---- Filters Panel ---- */
.filters-panel {
  position: relative;
  z-index: 2;
  box-sizing: border-box;
  max-width: 100%;
  overflow-x: hidden;
  overflow-y: visible;
  background: #ffffff;
  border-radius: 64rpx;
  padding: 32rpx 32rpx 28rpx;
  margin-bottom: 32rpx;
  box-shadow: 0 12rpx 32rpx rgba(0,0,0,0.06);
  border: 1rpx solid rgba(173,173,172,0.1);
}
.filter-section { padding: 8rpx 0; }
.filter-section-input {
  position: relative;
  z-index: 1;
  min-width: 0;
  max-width: 100%;
  pointer-events: auto;
}
.filter-input-shell {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  min-width: 0;
  min-height: 88rpx;
  pointer-events: auto;
}
/* H5 uni-input 默认 height:1.4em + overflow:hidden；勿把 wrapper 改成横向 flex，否则占位符会被裁切 */
.filter-input-shell :deep(uni-input) {
  display: block;
  width: 100% !important;
  max-width: 100% !important;
  min-height: 88rpx !important;
  height: auto !important;
  font-size: 26rpx !important;
  line-height: 1.5 !important;
  overflow: visible !important;
  box-sizing: border-box;
  pointer-events: auto !important;
}
.filter-input-shell :deep(.uni-input-wrapper) {
  width: 100% !important;
  max-width: 100% !important;
  min-height: 88rpx !important;
  height: auto !important;
  box-sizing: border-box;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  pointer-events: auto !important;
}
.filter-input-shell :deep(.uni-input-input) {
  height: auto !important;
  min-height: 44rpx !important;
  line-height: 1.5 !important;
  padding: 0 !important;
  pointer-events: auto !important;
}
.filter-input-shell :deep(.uni-input-placeholder) {
  line-height: 1.5 !important;
  max-height: none !important;
  overflow: visible !important;
}
.filter-input-shell :deep(input) {
  line-height: 1.5 !important;
  pointer-events: auto !important;
}
.filter-label {
  font-size: 22rpx; font-weight: 600; color: #a8a29e;
  display: block; margin-bottom: 14rpx;
  letter-spacing: 2rpx; text-transform: uppercase;
}
.filter-divider { height: 1rpx; background: #f0efee; margin: 16rpx 0; }
.chip-row { display: flex; flex-wrap: wrap; gap: 12rpx; }
.chip {
  padding: 14rpx 28rpx; border-radius: 9999rpx; font-size: 26rpx;
  background: #f5f5f4; color: #57534e;
  border: 1rpx solid #e7e5e4; font-weight: 500;
}
.chip-price {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 4rpx;
  padding: 12rpx 22rpx;
}
.chip-price-main {
  font-size: 28rpx;
  font-weight: 700;
  color: inherit;
}
.chip-price-sub {
  font-size: 22rpx;
  font-weight: 500;
  color: inherit;
  opacity: 0.85;
}
.chip-active {
  background: #9b3f00; color: #fff;
  border-color: #9b3f00;
  box-shadow: 0 8rpx 24rpx rgba(155,63,0,0.25);
}

/* ---- 我的位置 ---- */
.loc-section {
  padding-top: 4rpx;
}
.loc-hint {
  display: block;
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.5;
  margin-bottom: 16rpx;
}
.loc-hint.loc-hint-warn {
  color: #b45309;
}
.loc-settled {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 20rpx 24rpx;
  background: #f5f5f4;
  border-radius: 32rpx;
  border: 1rpx solid #e7e5e4;
}
.loc-settled-text {
  flex: 1;
  font-size: 26rpx;
  color: #44403c;
  line-height: 1.45;
  min-width: 0;
}
.loc-reset {
  font-size: 24rpx;
  font-weight: 600;
  color: #9b3f00;
  flex-shrink: 0;
}
.loc-setup {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.loc-actions {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 12rpx;
}
.loc-pill {
  padding: 16rpx 28rpx;
  border-radius: 9999rpx;
  background: #f5f5f4;
  border: 1rpx solid #e7e5e4;
}
.loc-pill-primary {
  background: rgba(155, 63, 0, 0.1);
  border-color: rgba(155, 63, 0, 0.25);
}
.loc-pill-text {
  font-size: 26rpx;
  font-weight: 600;
  color: #44403c;
}
.loc-pill-primary .loc-pill-text {
  color: #9b3f00;
}
.loc-geocode {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 12rpx;
  max-width: 100%;
}
.loc-geocode-input-shell {
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
}
.loc-fallback {
  font-size: 24rpx;
  color: #78716c;
  text-decoration: underline;
  text-align: center;
}
.trending-hint-warn {
  color: #b45309;
}

.filter-input {
  display: block;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-height: 88rpx;
  line-height: 1.5;
  background: #f5f5f4;
  border-radius: 48rpx;
  /* 内边距主要留给 uni-input 内部占位，避免与 .uni-input-input 双重挤压 */
  padding: 20rpx 28rpx;
  font-size: 26rpx;
  color: #1c1917;
  border: 1rpx solid #e7e5e4;
  pointer-events: auto;
}

/* ---- Trending Section ---- */
.trending-section { margin-top: 16rpx; }
.trending-heading {
  display: block; font-size: 34rpx; font-weight: 800;
  color: #1c1917; margin-bottom: 12rpx;
  letter-spacing: -1rpx;
}
.trending-hint {
  display: block; font-size: 22rpx; color: #a8a29e;
  line-height: 1.45; margin-bottom: 20rpx;
}
.trending-loading {
  padding: 40rpx 0;
  text-align: center;
}
.trending-loading-text { font-size: 26rpx; color: #a8a29e; }
.trending-empty {
  padding: 36rpx 24rpx;
  background: #fafaf9;
  border-radius: 32rpx;
  border: 1rpx solid #e7e5e4;
}
.trending-empty-text {
  font-size: 26rpx; color: #78716c; line-height: 1.55; text-align: center;
}
.trending-scroll {
  width: 100%;
  white-space: nowrap;
}
.trending-row {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  gap: 16rpx;
  padding-bottom: 8rpx;
}
.trending-card {
  flex-shrink: 0;
  width: 240rpx;
  background: #f1f1f0;
  border-radius: 64rpx;
  overflow: hidden;
}
.trending-img-wrap { height: 200rpx; overflow: hidden; margin: 16rpx 16rpx 0; border-radius: 48rpx; }
.trending-img { width: 100%; height: 100%; }
.trending-img-placeholder {
  width: 100%; height: 100%;
  background: linear-gradient(135deg, #d6d3d1, #a8a29e);
}
.trending-name {
  display: block; font-size: 26rpx; font-weight: 700;
  color: #1c1917; padding: 12rpx 20rpx 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.trending-meta {
  display: flex; align-items: center; gap: 6rpx;
  padding: 4rpx 20rpx 16rpx;
}
.trending-rating { font-size: 22rpx; font-weight: 600; color: #c2410c; }
.trending-dot { font-size: 22rpx; color: #a8a29e; }
.trending-distance { font-size: 22rpx; color: #71717a; }
.trending-category { font-size: 22rpx; color: #71717a; }
</style>

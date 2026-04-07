<template>
  <view class="page" v-if="restaurant">
    <!-- 自定义导航：custom 模式下系统不显示返回键 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarPx + 'px' }">
      <view class="nav-inner">
        <view class="nav-back" @click="goBack">
          <text class="nav-back-icon">‹</text>
        </view>
      </view>
    </view>

    <!-- Hero Image Section — matches Figma node 1001:379 -->
    <view class="hero">
      <image
        v-if="restaurant.image_url"
        class="hero-img"
        :src="restaurant.image_url"
        mode="aspectFill"
      />
      <view v-else class="hero-placeholder"></view>
      <!-- Gradient overlay from bottom — from-[rgba(0,0,0,0.6)] via-transparent -->
      <view class="hero-gradient"></view>
      <!-- Name & subtitle at bottom-left -->
      <view class="hero-content">
        <text class="hero-name">{{ restaurant.name }}</text>
        <text class="hero-sub">{{ restaurant.category || '美味餐厅' }}{{ restaurant.tags ? ' & ' + restaurant.tags.split(',')[0] : '' }}</text>
      </view>
      <!-- Floating pill badges overlapping hero bottom edge — Figma node 1001:385/390 -->
      <view class="hero-badges">
        <view class="badge" v-if="sourceLabel">
          <view class="badge-shadow"></view>
          <view class="badge-dot badge-dot-red"></view>
          <text class="badge-text">{{ sourceLabel }}</text>
        </view>
        <view class="badge" v-if="restaurant.rating != null">
          <view class="badge-shadow"></view>
          <view class="badge-dot badge-dot-blue"></view>
          <text class="badge-text">高德 {{ restaurant.rating }}</text>
        </view>
        <view class="badge" v-if="restaurant.dianping_rating != null">
          <view class="badge-shadow"></view>
          <view class="badge-dot badge-dot-orange"></view>
          <text class="badge-text">点评 {{ restaurant.dianping_rating }}</text>
        </view>
      </view>
    </view>

    <!-- Stats Card — Figma node 1001:396 -->
    <view class="stats-card">
      <view class="stats-card-shadow"></view>
      <view class="stats-inner">
        <!-- Price row — left: 价格档位, right: 人均 -->
        <view class="stats-top">
          <view class="stat-col">
            <text class="stat-label">价格档位</text>
            <text class="stat-value stat-value-primary">{{ restaurant.price_tier ? '¥' + restaurant.price_tier : '¥--' }}</text>
          </view>
          <view class="stat-col stat-col-right">
            <text class="stat-label">人均</text>
            <text class="stat-value">{{ restaurant.avg_price ? '¥' + restaurant.avg_price : '--' }}</text>
          </view>
        </view>
        <!-- Info rows with icon circles — Figma node 1001:411/416 -->
        <view class="stats-info">
          <view class="info-row" v-if="restaurant.address">
            <view class="info-icon-circle">
              <text class="info-icon-text">📍</text>
            </view>
            <text class="info-text">{{ restaurant.address }}</text>
          </view>
          <view class="info-row" v-if="restaurant.tags">
            <view class="info-icon-circle">
              <text class="info-icon-text">🏷</text>
            </view>
            <text class="info-text">{{ restaurant.tags }}</text>
          </view>
          <view class="info-row info-row-tap" v-if="restaurant.source_url" @click="openSourceUrl">
            <view class="info-icon-circle">
              <text class="info-icon-text">🔗</text>
            </view>
            <text class="info-text info-link">打开抖音 / 来源链接</text>
          </view>
        </view>
        <!-- Action buttons — Figma node 1001:422/425 -->
        <view class="stats-actions">
          <view class="btn-primary" @click="goRecord">
            <view class="btn-primary-shadow"></view>
            <text class="btn-primary-text">就这家了</text>
          </view>
          <view class="btn-secondary" @click="viewRoute">
            <view class="btn-secondary-icon-wrap">
              <text class="btn-secondary-icon-char">⊙</text>
            </view>
            <text class="btn-secondary-text">查看路线</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 评分与摘录：仅展示可核对来源；不编造点评正文 -->
    <view class="review-section" v-if="hasReviewSection">
      <view class="review-card">
        <text class="review-heading">评分从哪来</text>
        <text class="review-honest">
          大众点评等平台无面向本应用的开放接口，无法自动拉取。以下评分、链接与摘录须由录入者在官方页核对后填写；未填写则表示暂无收录。
        </text>

        <view class="review-item" v-if="restaurant.rating != null">
          <view class="review-icon-circle review-icon-circle-blue">
            <text class="ri-char">高</text>
          </view>
          <view class="review-body">
            <view class="review-head">
              <text class="review-source">高德地图</text>
              <view class="badge-tag badge-tag-blue">
                <text class="badge-tag-text">POI 评分</text>
              </view>
            </view>
            <text class="review-fact">商户页展示评分（五星制）：<text class="review-strong">{{ restaurant.rating }}</text> / 5</text>
            <text class="review-hint">来自高德 POI 数据，与地图/导航一致。</text>
          </view>
        </view>

        <view class="review-item" v-if="hasDianpingBlock">
          <view class="review-icon-circle">
            <text class="ri-char">点</text>
          </view>
          <view class="review-body">
            <view class="review-head">
              <text class="review-source">大众点评</text>
              <view v-if="restaurant.dianping_rating != null" class="badge-tag badge-tag-orange">
                <text class="badge-tag-text">{{ restaurant.dianping_rating }} 星</text>
              </view>
            </view>
            <text v-if="restaurant.dianping_rating != null" class="review-fact">
              店铺页展示评分：<text class="review-strong">{{ restaurant.dianping_rating }}</text> / 5（录入核对）
            </text>
            <view v-if="dianpingSnippetSafe" class="snippet-box">
              <text class="review-quote">「{{ dianpingSnippetSafe }}」</text>
              <text class="snippet-note">摘录自大众点评 · 请在官方页核对原文</text>
            </view>
            <view v-if="restaurant.dianping_url" class="link-open" @click="openDianping">
              <text class="link-open-text">打开大众点评店铺页</text>
            </view>
          </view>
        </view>
        <view v-else class="review-placeholder">
          <text class="review-placeholder-t">暂无大众点评收录：可在「发现 → 编辑餐厅」中填写店铺链接、星级与一句原文摘录。</text>
        </view>

        <view class="review-item" v-if="hasAuthorityBlock">
          <view class="review-icon-circle review-icon-circle-gold">
            <text class="ri-char">榜</text>
          </view>
          <view class="review-body">
            <view class="review-head">
              <text class="review-source">{{ restaurant.authority_label || '其它权威来源' }}</text>
              <view v-if="restaurant.authority_rating != null" class="badge-tag badge-tag-gold">
                <text class="badge-tag-text">{{ restaurant.authority_rating }}</text>
              </view>
            </view>
            <text v-if="restaurant.authority_rating != null" class="review-fact">
              参考评分：<text class="review-strong">{{ restaurant.authority_rating }}</text>（录入核对）
            </text>
            <view v-if="restaurant.authority_url" class="link-open" @click="openAuthority">
              <text class="link-open-text">打开官方/榜单页面</text>
            </view>
          </view>
        </view>

        <view class="compare-section" v-if="comparePairs.length >= 2">
          <text class="compare-label">多来源对比</text>
          <view class="compare-chips">
            <text v-for="(c, i) in comparePairs" :key="i" class="compare-chip">{{ c.label }} {{ c.value }}/5</text>
          </view>
        </view>
      </view>
    </view>

    <!-- Map Section — H5/小程序/App 使用 <map> 原生组件（可拖动缩放）；需配置 manifest h5.sdkConfigs.maps.amap -->
    <view class="map-section" v-if="restaurant.address">
      <view class="map-card">
        <map
          v-if="hasMapCoords"
          id="detailMap"
          class="map-native"
          :latitude="mapLat"
          :longitude="mapLng"
          :scale="mapScale"
          :markers="mapMarkers"
          :enable-scroll="true"
          :enable-zoom="true"
          :show-location="true"
          :enable-satellite="mapSatellite"
        />
        <view v-if="hasMapCoords" class="map-layer-toggle" @click.stop>
          <view
            :class="['layer-chip', !mapSatellite && 'layer-chip-active']"
            @click="mapSatellite = false"
          >
            <text class="layer-chip-text">地图</text>
          </view>
          <view
            :class="['layer-chip', mapSatellite && 'layer-chip-active']"
            @click="mapSatellite = true"
          >
            <text class="layer-chip-text">卫星</text>
          </view>
        </view>
        <view v-else class="map-fallback">
          <text class="map-fallback-text">{{ mapFallbackText }}</text>
        </view>
        <!-- Bottom overlay — 不罩住整张图，避免阻挡地图拖拽；仅底部条可点「路线」 -->
        <view class="map-overlay">
          <view class="map-info">
            <text class="map-eyebrow">位置</text>
            <text class="map-address">{{ shortAddress }}</text>
          </view>
          <view class="map-arrow" @click="viewRoute">
            <text class="map-arrow-icon">→</text>
          </view>
        </view>
      </view>
    </view>

    <view style="height: 60rpx;"></view>
  </view>

  <!-- Loading State -->
  <view v-else class="loading-page">
    <view class="loading-spinner"></view>
    <text class="loading-text">加载中</text>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { restaurantApi, amapApi } from '../../api'

const restaurant = ref(null)
const statusBarPx = ref(20)
const geocodeDone = ref(false)
/** H5 会触发浏览器定位授权，用于在地图上显示「我的位置」 */
const mapScale = 17
const mapSatellite = ref(false)

const sourceLabel = computed(() => {
  const map = { douyin: '抖音热门', amap: '高德推荐', dianping: '点评精选', manual: '手动添加' }
  return map[restaurant.value?.source] || restaurant.value?.source || '本地发现'
})

const shortAddress = computed(() => {
  const addr = restaurant.value?.address || ''
  // Show last meaningful part of address
  if (addr.length > 8) {
    const idx = addr.indexOf('区')
    if (idx > 0 && idx < addr.length - 1) return addr.substring(idx + 1)
    return addr.substring(addr.length - 8)
  }
  return addr
})

const hasReviewSection = computed(() => !!restaurant.value)

const hasDianpingBlock = computed(() => {
  const r = restaurant.value
  if (!r) return false
  const sn = (r.dianping_snippet || '').trim()
  return (
    r.dianping_rating != null ||
    !!(r.dianping_url || '').trim() ||
    !!sn
  )
})

const dianpingSnippetSafe = computed(() => {
  const s = (restaurant.value?.dianping_snippet || '').trim()
  return s.length > 200 ? `${s.slice(0, 200)}…` : s
})

const hasAuthorityBlock = computed(() => {
  const r = restaurant.value
  if (!r) return false
  return (
    !!(r.authority_label || '').trim() ||
    r.authority_rating != null ||
    !!(r.authority_url || '').trim()
  )
})

const comparePairs = computed(() => {
  const r = restaurant.value
  if (!r) return []
  const out = []
  if (r.rating != null && Number.isFinite(Number(r.rating))) {
    out.push({ label: '高德', value: Number(r.rating).toFixed(1) })
  }
  if (r.dianping_rating != null && Number.isFinite(Number(r.dianping_rating))) {
    out.push({ label: '大众点评', value: Number(r.dianping_rating).toFixed(1) })
  }
  if (r.authority_rating != null && Number.isFinite(Number(r.authority_rating))) {
    const lb = (r.authority_label || '').trim() || '其它来源'
    out.push({ label: lb, value: Number(r.authority_rating).toFixed(1) })
  }
  return out
})

const mapLat = computed(() => {
  const v = Number(restaurant.value?.latitude)
  return Number.isFinite(v) ? v : 0
})

const mapLng = computed(() => {
  const v = Number(restaurant.value?.longitude)
  return Number.isFinite(v) ? v : 0
})

const hasMapCoords = computed(() => {
  const lat = mapLat.value
  const lng = mapLng.value
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false
  if (Math.abs(lat) < 1e-6 && Math.abs(lng) < 1e-6) return false
  return true
})

const mapMarkers = computed(() => {
  if (!hasMapCoords.value || !restaurant.value) return []
  const name = (restaurant.value.name || '餐厅').trim()
  const calloutText = name.length > 22 ? `${name.slice(0, 22)}…` : name
  return [
    {
      id: 1,
      latitude: mapLat.value,
      longitude: mapLng.value,
      title: name,
      width: 32,
      height: 32,
      callout: {
        content: calloutText,
        color: '#2e2f2f',
        fontSize: 13,
        borderRadius: 12,
        bgColor: '#ffffff',
        padding: 8,
        display: 'ALWAYS',
        textAlign: 'center',
      },
    },
  ]
})

const mapFallbackText = computed(() => {
  if (!restaurant.value?.address) return '暂无地址信息'
  if (!geocodeDone.value) return '正在解析位置…'
  return '无法显示地图：H5 请配置高德 Web 端的 AMAP_WEB_KEY 和 AMAP_WEB_SECURITY_JS_CODE；小程序/App 使用端自带地图。地理编码仍依赖后端 Web 服务 Key。'
})

const goBack = () => {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack({
      fail: () => uni.switchTab({ url: '/pages/pick/pick' }),
    })
  } else {
    uni.switchTab({ url: '/pages/pick/pick' })
  }
}

function openExternalUrl(u) {
  if (!u || typeof u !== 'string') return
  const url = u.trim()
  if (!url) return
  // #ifdef H5
  window.open(url, '_blank', 'noopener,noreferrer')
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: url,
    success: () => uni.showToast({ title: '链接已复制，请到浏览器打开', icon: 'none' }),
  })
  // #endif
}

const openSourceUrl = () => {
  openExternalUrl(restaurant.value?.source_url)
}

const openDianping = () => {
  openExternalUrl(restaurant.value?.dianping_url)
}

const openAuthority = () => {
  openExternalUrl(restaurant.value?.authority_url)
}

async function enrichLocationFromAddress() {
  const r = restaurant.value
  if (!r?.address) {
    geocodeDone.value = true
    return
  }
  const hasCoords =
    r.latitude != null &&
    r.longitude != null &&
    Number.isFinite(Number(r.latitude)) &&
    Number.isFinite(Number(r.longitude)) &&
    !(Number(r.latitude) === 0 && Number(r.longitude) === 0)
  if (hasCoords) {
    geocodeDone.value = true
    return
  }
  try {
    const geo = await amapApi.geocode(r.address)
    if (geo && geo.code === 200 && geo.data) {
      const lat = geo.data.latitude
      const lng = geo.data.longitude
      restaurant.value = {
        ...r,
        latitude: lat,
        longitude: lng,
      }
      try {
        const saved = await restaurantApi.update(
          r.id,
          { latitude: lat, longitude: lng },
          { silent: true }
        )
        restaurant.value = saved
      } catch (_) {
        /* 静默失败：界面仍可用本地坐标，仅未持久化 */
      }
    }
  } catch (_) {
    /* toast 已在 request 中处理或静默 */
  } finally {
    geocodeDone.value = true
  }
}

const goRecord = () => {
  const r = restaurant.value
  uni.navigateTo({
    url: `/pages/records/add?restaurant_id=${r.id}&restaurant_name=${encodeURIComponent(r.name)}`
  })
}

const viewRoute = () => {
  const r = restaurant.value
  if (r.latitude && r.longitude) {
    const url = `https://uri.amap.com/marker?position=${r.longitude},${r.latitude}&name=${encodeURIComponent(r.name)}`
    // #ifdef H5
    window.open(url)
    // #endif
    // #ifndef H5
    uni.openLocation({
      latitude: r.latitude,
      longitude: r.longitude,
      name: r.name,
      address: r.address
    })
    // #endif
  } else if (r.address) {
    const url = `https://uri.amap.com/search?keyword=${encodeURIComponent(r.name)}&city=成都`
    // #ifdef H5
    window.open(url)
    // #endif
  } else {
    uni.showToast({ title: '暂无位置信息', icon: 'none' })
  }
}

onMounted(() => {
  try {
    const sys = uni.getSystemInfoSync()
    statusBarPx.value = sys.statusBarHeight || 20
  } catch (_) {
    statusBarPx.value = 20
  }
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  const options = currentPage.$page ? currentPage.$page.options : currentPage.options
  if (options && options.id) {
    loadRestaurant(parseInt(options.id))
  }
})

const loadRestaurant = async (id) => {
  geocodeDone.value = false
  try {
    restaurant.value = await restaurantApi.get(id)
    await enrichLocationFromAddress()
  } catch (e) {
    geocodeDone.value = true
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
}
</script>

<style scoped>
/* ============================================
   Detail Page — Pixel-matching Figma design
   fileKey: adHGiSXgTsxgpKNZOWNrzu node: 1001:377
   ============================================ */

.page {
  min-height: 100vh;
  background: var(--color-bg);
  padding-bottom: env(safe-area-inset-bottom);
}

/* 自定义顶栏返回 */
.nav-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 200;
  pointer-events: none;
}
.nav-inner {
  height: 88rpx;
  display: flex;
  align-items: center;
  padding-left: 16rpx;
  padding-right: 24rpx;
}
.nav-back {
  pointer-events: auto;
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.38);
  display: flex;
  align-items: center;
  justify-content: center;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}
.nav-back-icon {
  color: #fff;
  font-size: 52rpx;
  font-weight: 300;
  line-height: 1;
  margin-top: -6rpx;
}

/* ─── Hero Section ─── Figma: 1001:379 */
.hero {
  position: relative;
  width: 100%;
  height: 640rpx;
  overflow: visible; /* badges overflow bottom */
}
.hero-img {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
.hero-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(160deg, #1a1a1a 0%, #2e2f2f 40%, #4a3728 100%);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
.hero-gradient {
  position: absolute;
  left: 0; right: 0; bottom: 0; top: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.15) 40%, rgba(0,0,0,0) 60%);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  pointer-events: none;
}
.hero-content {
  position: absolute;
  bottom: 100rpx;
  left: 40rpx;
  right: 200rpx;
}
.hero-name {
  display: block;
  font-size: 64rpx;
  font-weight: 700;
  color: #fff;
  letter-spacing: -2rpx;
  line-height: 1.1;
  text-shadow: 0 2rpx 8rpx rgba(0,0,0,0.3);
}
.hero-sub {
  display: block;
  font-size: 28rpx;
  color: rgba(255,255,255,0.9);
  margin-top: 12rpx;
  font-weight: 500;
}

/* ─── Floating Badges ─── Figma: 1001:385 */
.hero-badges {
  position: absolute;
  bottom: -30rpx;
  right: 32rpx;
  display: flex;
  gap: 14rpx;
  z-index: 10;
}
.badge {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12rpx;
  background: #fff;
  border: 1rpx solid var(--color-border);
  border-radius: var(--radius-full);
  padding: 16rpx 34rpx;
  height: 72rpx;
}
.badge-shadow {
  position: absolute;
  inset: -1rpx;
  border-radius: var(--radius-full);
  box-shadow: 0 40rpx 50rpx -10rpx rgba(0,0,0,0.1), 0 16rpx 20rpx -12rpx rgba(0,0,0,0.1);
  pointer-events: none;
}
.badge-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
}
.badge-dot-red { background: #ef4444; }
.badge-dot-blue { background: #3b82f6; }
.badge-dot-orange { background: #ea580c; }
.badge-text {
  font-size: 26rpx;
  color: var(--color-text);
  font-weight: 500;
  line-height: 1;
}

/* ─── Stats Card ─── Figma: 1001:396 */
.stats-card {
  position: relative;
  margin: 56rpx 32rpx 0;
  background: #fff;
  border: 1rpx solid var(--color-border-light);
  border-radius: var(--radius-xl);
}
.stats-card-shadow {
  position: absolute;
  inset: -1rpx;
  border-radius: var(--radius-xl);
  box-shadow: 0 50rpx 100rpx -24rpx rgba(124,45,18,0.05);
  pointer-events: none;
}
.stats-inner {
  position: relative;
  padding: 48rpx;
}
.stats-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: 36rpx;
}
.stat-col {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.stat-col-right { align-items: flex-end; }
.stat-label {
  font-size: 26rpx;
  color: var(--color-text-muted);
  font-weight: 500;
  line-height: 36rpx;
}
.stat-value {
  font-size: 44rpx;
  font-weight: 700;
  color: var(--color-text);
  line-height: 56rpx;
}
.stat-value-primary {
  color: var(--color-primary);
}

/* Info rows */
.stats-info {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding-bottom: 40rpx;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 18rpx;
}
.info-icon-circle {
  width: 36rpx;
  height: 36rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.info-icon-text {
  font-size: 28rpx;
  line-height: 1;
}
.info-text {
  font-size: 26rpx;
  color: var(--color-text-secondary);
  line-height: 36rpx;
  font-weight: 500;
}
.info-row-tap:active {
  opacity: 0.85;
}
.info-link {
  color: #9b3f00;
  text-decoration: underline;
}

/* Action buttons */
.stats-actions {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.btn-primary {
  position: relative;
  background: var(--color-primary-gradient);
  border-radius: var(--radius-full);
  padding: 28rpx;
  text-align: center;
}
.btn-primary-shadow {
  position: absolute;
  inset: 0;
  border-radius: var(--radius-full);
  box-shadow: 0 20rpx 30rpx -6rpx rgba(155,63,0,0.2), 0 8rpx 12rpx -8rpx rgba(155,63,0,0.2);
  pointer-events: none;
}
.btn-primary-text {
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
  line-height: 40rpx;
}
.btn-secondary {
  background: #e2e2e1;
  border-radius: var(--radius-full);
  padding: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
}
.btn-secondary-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-secondary-icon-char {
  font-size: 28rpx;
  color: var(--color-text);
}
.btn-secondary-text {
  color: var(--color-text);
  font-size: 30rpx;
  font-weight: 600;
  line-height: 40rpx;
}

/* ─── Review Card ─── Figma: 1001:470 */
.review-section {
  margin: 48rpx 32rpx 0;
}
.review-card {
  background: rgba(255,195,189,0.2);
  border: 1rpx solid rgba(255,195,189,0.3);
  border-radius: var(--radius-xl);
  padding: 48rpx;
}
.review-heading {
  display: block;
  font-size: 48rpx;
  font-weight: 700;
  color: var(--color-text);
  line-height: 60rpx;
  margin-bottom: 20rpx;
}
.review-honest {
  display: block;
  font-size: 24rpx;
  color: var(--color-text-muted);
  line-height: 1.55;
  margin-bottom: 36rpx;
}
.review-fact {
  display: block;
  font-size: 28rpx;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin-top: 8rpx;
}
.review-strong {
  font-weight: 800;
  color: var(--color-text);
}
.review-hint {
  display: block;
  font-size: 24rpx;
  color: var(--color-text-muted);
  margin-top: 8rpx;
  line-height: 1.45;
}
.snippet-box {
  margin-top: 16rpx;
  padding: 20rpx;
  background: rgba(255, 255, 255, 0.65);
  border-radius: var(--radius-lg);
}
.snippet-note {
  display: block;
  font-size: 22rpx;
  color: var(--color-text-muted);
  margin-top: 12rpx;
}
.link-open {
  margin-top: 16rpx;
  align-self: flex-start;
}
.link-open-text {
  font-size: 26rpx;
  font-weight: 600;
  color: #9b3f00;
  text-decoration: underline;
}
.review-placeholder {
  padding: 24rpx;
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-lg);
  margin-bottom: 32rpx;
}
.review-placeholder-t {
  font-size: 26rpx;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
.review-icon-circle-gold {
  background: #fffbeb;
}
.badge-tag-gold {
  background: #fef3c7;
}
.badge-tag-gold .badge-tag-text {
  color: #92400e;
}
.compare-section {
  border-top: 1rpx solid rgba(173, 173, 172, 0.25);
  padding-top: 32rpx;
  margin-top: 8rpx;
}
.compare-label {
  display: block;
  font-size: 26rpx;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 16rpx;
}
.compare-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.compare-chip {
  font-size: 24rpx;
  font-weight: 600;
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.8);
  padding: 12rpx 20rpx;
  border-radius: var(--radius-full);
  border: 1rpx solid rgba(173, 173, 172, 0.25);
}
.review-item {
  display: flex;
  gap: 24rpx;
  margin-bottom: 40rpx;
}
.review-icon-circle {
  width: 80rpx;
  height: 80rpx;
  background: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2rpx 4rpx rgba(0,0,0,0.05);
  flex-shrink: 0;
}
.review-icon-circle-blue {
  background: #fff;
}
.ri-char {
  font-size: 36rpx;
  line-height: 1;
}
.review-body {
  flex: 1;
  min-width: 0;
}
.review-head {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 6rpx;
}
.review-source {
  font-size: 32rpx;
  color: var(--color-text);
  font-weight: 600;
  line-height: 48rpx;
}
.badge-tag {
  padding: 4rpx 16rpx;
  border-radius: var(--radius-full);
}
.badge-tag-orange {
  background: #ffedd5;
}
.badge-tag-orange .badge-tag-text {
  color: #9a3412;
}
.badge-tag-blue {
  background: #dbeafe;
}
.badge-tag-blue .badge-tag-text {
  color: #1e40af;
}
.badge-tag-text {
  font-size: 22rpx;
  font-weight: 600;
  line-height: 28rpx;
}
.review-quote {
  display: block;
  font-size: 28rpx;
  color: var(--color-text-secondary);
  line-height: 40rpx;
  font-style: italic;
}

/* ─── Map Card ─── Figma: 1001:508 */
.map-section {
  margin: 48rpx 32rpx 0;
}
.map-card {
  position: relative;
  height: 560rpx;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: #e8e8e7;
  box-shadow: 0 50rpx 100rpx -24rpx rgba(124,45,18,0.05);
}
.map-native {
  width: 100%;
  height: 560rpx;
  display: block;
}
.map-layer-toggle {
  position: absolute;
  top: 24rpx;
  right: 24rpx;
  z-index: 3;
  display: flex;
  flex-direction: row;
  gap: 8rpx;
  background: rgba(255, 255, 255, 0.94);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border-radius: var(--radius-md);
  padding: 6rpx;
  box-shadow: var(--shadow-sm);
}
.layer-chip {
  padding: 10rpx 22rpx;
  border-radius: 16rpx;
}
.layer-chip-active {
  background: var(--color-primary-bg);
}
.layer-chip-text {
  font-size: 24rpx;
  color: var(--color-text-secondary);
}
.layer-chip-active .layer-chip-text {
  color: var(--color-primary);
  font-weight: 600;
}
.map-fallback {
  width: 100%;
  height: 100%;
  background: linear-gradient(160deg, #ddd 0%, #e8e8e7 40%, #d5d5d4 100%);
  opacity: 0.85;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
  box-sizing: border-box;
}
.map-fallback-text {
  font-size: 28rpx;
  color: var(--color-text-secondary);
  text-align: center;
  line-height: 1.5;
}
/* Bottom overlay — Figma: 1001:515 */
.map-overlay {
  position: absolute;
  left: 32rpx;
  right: 32rpx;
  bottom: 32rpx;
  z-index: 2;
  pointer-events: auto;
  background: rgba(255,255,255,0.92);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-xl);
  padding: 32rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.map-info {
  flex: 1;
  min-width: 0;
}
.map-eyebrow {
  display: block;
  font-size: 22rpx;
  color: var(--color-primary);
  letter-spacing: 2rpx;
  text-transform: uppercase;
  font-weight: 500;
  line-height: 28rpx;
}
.map-address {
  display: block;
  font-size: 30rpx;
  color: var(--color-text);
  font-weight: 600;
  margin-top: 4rpx;
  line-height: 40rpx;
}
.map-arrow {
  width: 72rpx;
  height: 72rpx;
  background: var(--color-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 20rpx 30rpx -6rpx rgba(0,0,0,0.1), 0 8rpx 12rpx -8rpx rgba(0,0,0,0.1);
}
.map-arrow-icon {
  color: #fff;
  font-size: 30rpx;
  font-weight: 700;
}

/* ─── Loading ─── */
.loading-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
}
.loading-spinner {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  border: 4rpx solid var(--color-border);
  border-top-color: var(--color-primary);
  animation: spin 0.8s linear infinite;
  margin-bottom: 20rpx;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text {
  font-size: 28rpx;
  color: var(--color-text-muted);
}
</style>

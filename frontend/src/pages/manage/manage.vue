<template>
  <view class="page">
    <!-- Header — 发现美食 + 榜单 -->
    <view class="header-section">
      <view class="header-row">
        <text class="header-title">发现美食</text>
      </view>
      <view class="header-actions">
        <view class="btn-batch" @click="goMapBatch">
          <text class="btn-batch-text">地图批量加</text>
        </view>
        <view class="btn-add" @click="goAdd">
          <text class="btn-add-text">+ 新增</text>
        </view>
      </view>
      <view class="tool-row">
        <view class="tool-pill" @click="goDouyinImport"><text class="tool-pill-t">抖音链接</text></view>
        <view class="tool-pill" @click="goScreenshotImport"><text class="tool-pill-t">截图识别</text></view>
      </view>
    </view>

    <scroll-view class="tabs-scroll" scroll-x :show-scrollbar="false">
      <view class="tabs-inner">
        <view
          v-for="t in tabs"
          :key="t.key || 'all'"
          :class="['tab', activeBoard === t.key ? 'tab-on' : '']"
          @click="onTab(t.key)"
        >
          <text class="tab-text">{{ t.label }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- Search -->
    <view class="search-wrap">
      <input class="search-input" v-model="keyword" placeholder="搜索餐厅..." @confirm="fetchList" />
    </view>

    <!-- Trending Hero — Figma major card + minor stack -->
    <view class="trending-hero" v-if="!keyword && featuredList.length > 0">
      <view class="hero-major" @click="goDetail(featuredList[0])" v-if="featuredList[0]">
        <view class="major-card">
          <image v-if="featuredList[0].image_url" class="major-img" :src="featuredList[0].image_url" mode="aspectFill" />
          <view v-else class="major-img major-img-placeholder"></view>
          <view class="major-gradient"></view>
          <view class="major-content">
            <view class="major-badge">
              <text class="major-badge-text">{{ heroBadgeText }}</text>
            </view>
            <text class="major-name">{{ featuredList[0].name }}</text>
            <text class="major-sub">{{ featuredList[0].category || '精选推荐' }}</text>
          </view>
        </view>
      </view>
      <view class="hero-minor-stack" v-if="featuredList.length > 1">
        <view
          v-for="r in featuredList.slice(1, 3)"
          :key="r.id"
          class="minor-card"
          @click="goDetail(r)"
        >
          <image v-if="r.image_url" class="minor-img" :src="r.image_url" mode="aspectFill" />
          <view v-else class="minor-img minor-img-placeholder"></view>
          <view class="minor-info">
            <text class="minor-name">{{ r.name }}</text>
            <text class="minor-cat">{{ r.category || '--' }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- Restaurant Grid — Figma card grid -->
    <view class="grid-section" v-if="restaurants.length > 0">
      <text class="grid-heading">{{ gridHeading }}</text>
      <view class="restaurant-grid">
        <view
          v-for="r in restaurants"
          :key="r.id"
          class="grid-card"
          @click="goDetail(r)"
        >
          <!-- Image with badge -->
          <view class="grid-card-img-wrap">
            <image v-if="r.image_url" class="grid-card-img" :src="r.image_url" mode="aspectFill" />
            <view v-else class="grid-card-img grid-card-img-placeholder"></view>
            <view class="grid-status-badge" v-if="r.source && r.source !== 'manual'">
              <text class="grid-badge-text">{{ { douyin: '抖音', amap: '高德', dianping: '点评' }[r.source] || r.source }}</text>
            </view>
          </view>
          <!-- Info -->
          <view class="grid-card-info">
            <text class="grid-card-name">{{ r.name }}</text>
            <view class="grid-card-row">
              <text class="grid-card-rating" v-if="r.rating">{{ r.rating }}★</text>
              <text class="grid-card-price" v-if="r.avg_price">¥{{ r.avg_price }}/人</text>
            </view>
            <view class="grid-card-tags" v-if="r.category || r.price_tier">
              <text class="grid-tag" v-if="r.category">{{ r.category }}</text>
              <text class="grid-tag" v-if="r.price_tier">{{ r.price_tier }}</text>
            </view>
          </view>
          <!-- Actions -->
          <view class="grid-card-actions">
            <view class="grid-action" @click.stop="goEdit(r)">
              <text class="grid-action-text">编辑</text>
            </view>
            <view class="grid-action grid-action-danger" @click.stop="confirmDelete(r)">
              <text class="grid-action-text-danger">删除</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Empty State -->
    <view v-if="restaurants.length === 0" class="empty-card">
      <text class="empty-icon">🍜</text>
      <text class="empty-title">{{ emptyTitle }}</text>
      <text class="empty-desc">{{ emptyDesc }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { restaurantApi, checkAuthGate } from '../../api'

const tabs = [
  { key: '', label: '全部' },
  { key: 'my_pick', label: '自己精选' },
  { key: 'viral', label: '网红打卡' },
  { key: 'high_score', label: '高分推荐' },
]

const restaurants = ref([])
const keyword = ref('')
const activeBoard = ref('')

const featuredList = computed(() => {
  const list = [...restaurants.value]
  list.sort((a, b) => (b.rating || 0) - (a.rating || 0))
  return list.slice(0, 3)
})

const heroBadgeText = computed(() => {
  const m = {
    '': '✨ 推荐',
    my_pick: '❤️ 我的精选',
    viral: '📱 网红打卡',
    high_score: '⭐ 高分',
  }
  return m[activeBoard.value] || '✨ 推荐'
})

const gridHeading = computed(() => {
  if (keyword.value) return '搜索结果'
  const m = {
    '': '全部餐厅',
    my_pick: '自己精选',
    viral: '网红打卡（抖音向 · 可配视频链接）',
    high_score: '高分推荐（评分≥4.5）',
  }
  return m[activeBoard.value] || '全部餐厅'
})

const emptyTitle = computed(() => {
  if (keyword.value) return '没有匹配的餐厅'
  const m = {
    '': '还没有餐厅',
    my_pick: '自己精选还是空的',
    viral: '暂无网红打卡数据',
    high_score: '暂无高分店铺',
  }
  return m[activeBoard.value] || '还没有餐厅'
})

const emptyDesc = computed(() => {
  const m = {
    '': '用「地图批量加」从高德搜店，或点「+ 新增」',
    my_pick: '点「地图批量加」勾选 POI，或编辑餐厅勾选「自己精选」',
    viral: '运行 backend 脚本 seed_viral_board.py 可看示例；也可手动新增并勾选「网红打卡」',
    high_score: '在编辑里把评分调到 4.5+，或为高德导入数据',
  }
  return m[activeBoard.value] || ''
})

const onTab = (key) => {
  activeBoard.value = key
  fetchList()
}

const fetchList = async () => {
  const params = { limit: 200 }
  if (keyword.value) params.keyword = keyword.value
  if (activeBoard.value) params.board = activeBoard.value
  restaurants.value = await restaurantApi.list(params)
}

const goMapBatch = () => {
  uni.navigateTo({ url: '/pages/manage/map-poi-batch' })
}

const goDouyinImport = () => {
  uni.navigateTo({ url: '/pages/manage/douyin-import' })
}

const goScreenshotImport = () => {
  uni.navigateTo({ url: '/pages/manage/screenshot-import' })
}

const goAdd = () => {
  uni.navigateTo({ url: '/pages/manage/edit' })
}

const goEdit = (r) => {
  uni.navigateTo({ url: `/pages/manage/edit?id=${r.id}` })
}

const goDetail = (r) => {
  uni.navigateTo({ url: `/pages/detail/detail?id=${r.id}` })
}

const confirmDelete = (r) => {
  uni.showModal({
    title: '确认删除',
    content: `确定删除「${r.name}」吗？`,
    success: async (res) => {
      if (res.confirm) {
        await restaurantApi.remove(r.id)
        uni.showToast({ title: '已删除' })
        fetchList()
      }
    }
  })
}

onShow(async () => {
  if (!(await checkAuthGate())) return
  fetchList()
})
</script>

<style scoped>
.page {
  padding: 40rpx 32rpx 120rpx;
  min-height: 100vh;
  background: #f7f6f5;
}

/* ---- Header ---- */
.header-section { margin-bottom: 20rpx; }
.header-row {
  display: flex; justify-content: space-between;
  align-items: center;
}
.header-title {
  font-size: 52rpx; font-weight: 900; color: #1c1917;
  letter-spacing: -2rpx;
}
.header-actions {
  display: flex;
  flex-direction: row;
  gap: 16rpx;
  margin-top: 20rpx;
  flex-wrap: wrap;
}
.btn-batch {
  flex: 1;
  min-width: 200rpx;
  background: #fff;
  border: 2rpx solid #9b3f00;
  border-radius: 9999rpx;
  padding: 14rpx 28rpx;
  text-align: center;
}
.btn-batch-text {
  font-size: 26rpx;
  font-weight: 700;
  color: #9b3f00;
}
.btn-add {
  flex: 1;
  min-width: 160rpx;
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  border-radius: 9999rpx; padding: 14rpx 32rpx;
  box-shadow: 0 12rpx 36rpx rgba(155,63,0,0.25);
  text-align: center;
}
.btn-add:active { opacity: 0.9; }
.btn-add-text { font-size: 26rpx; font-weight: 700; color: #fff; }

.tabs-scroll {
  width: 100%;
  margin-bottom: 20rpx;
  white-space: nowrap;
}
.tabs-inner {
  display: inline-flex;
  flex-direction: row;
  gap: 12rpx;
  padding: 4rpx 0 12rpx;
}
.tab {
  display: inline-flex;
  padding: 14rpx 28rpx;
  border-radius: 9999rpx;
  background: #fff;
  border: 1rpx solid #e7e5e4;
}
.tab-on {
  background: #1c1917;
  border-color: #1c1917;
}
.tab-text {
  font-size: 24rpx;
  font-weight: 600;
  color: #57534e;
}
.tab-on .tab-text {
  color: #fff;
}

.tool-row {
  display: flex;
  flex-direction: row;
  gap: 12rpx;
  margin-top: 16rpx;
  flex-wrap: wrap;
}
.tool-pill {
  padding: 12rpx 24rpx;
  border-radius: 9999rpx;
  background: #fafaf9;
  border: 1rpx solid #e7e5e4;
}
.tool-pill-t {
  font-size: 22rpx;
  font-weight: 600;
  color: #57534e;
}

/* ---- Search ---- */
.search-wrap { margin-bottom: 24rpx; }
.search-input {
  background: #ffffff; border-radius: 48rpx;
  padding: 24rpx 32rpx; font-size: 28rpx; color: #1c1917;
  border: 1rpx solid #e7e5e4;
  box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.04);
}

/* ---- Trending Hero ---- */
.trending-hero {
  display: flex; gap: 16rpx; margin-bottom: 32rpx;
  min-height: 320rpx;
}
.hero-major { flex: 1.4; min-width: 0; }
.major-card {
  position: relative; border-radius: 48rpx; overflow: hidden;
  height: 100%; min-height: 320rpx;
}
.major-img {
  width: 100%; height: 100%; position: absolute; inset: 0;
}
.major-img-placeholder {
  background: linear-gradient(135deg, #44403c, #78716c);
}
.major-gradient {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.65) 0%, transparent 60%);
}
.major-content {
  position: absolute; bottom: 24rpx; left: 24rpx; right: 24rpx;
  z-index: 1;
}
.major-badge {
  display: inline-block; background: rgba(155,63,0,0.9);
  border-radius: 9999rpx; padding: 8rpx 20rpx;
  margin-bottom: 8rpx;
}
.major-badge-text { font-size: 22rpx; font-weight: 700; color: #fff; }
.major-name {
  display: block; font-size: 36rpx; font-weight: 900; color: #fff;
  line-height: 1.2;
}
.major-sub {
  display: block; font-size: 24rpx; color: rgba(255,255,255,0.8);
  margin-top: 4rpx;
}

.hero-minor-stack {
  flex: 1; display: flex; flex-direction: column; gap: 16rpx;
}
.minor-card {
  flex: 1; background: #ffffff; border-radius: 32rpx;
  overflow: hidden; display: flex;
  box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.04);
}
.minor-img {
  width: 160rpx; height: 100%; flex-shrink: 0;
}
.minor-img-placeholder { background: linear-gradient(135deg, #d6d3d1, #a8a29e); }
.minor-info {
  padding: 16rpx 20rpx; flex: 1; min-width: 0;
  display: flex; flex-direction: column; justify-content: center;
}
.minor-name {
  font-size: 26rpx; font-weight: 700; color: #1c1917;
  display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.minor-cat { font-size: 22rpx; color: #78716c; display: block; margin-top: 4rpx; }

/* ---- Grid Section ---- */
.grid-section { margin-top: 8rpx; }
.grid-heading {
  display: block; font-size: 34rpx; font-weight: 800;
  color: #1c1917; margin-bottom: 20rpx;
  letter-spacing: -1rpx;
}
.restaurant-grid {
  display: flex; flex-wrap: wrap; gap: 16rpx;
}
.grid-card {
  width: calc(50% - 8rpx); background: #ffffff;
  border-radius: 48rpx; overflow: hidden;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.04);
  border: 1rpx solid rgba(173,173,172,0.08);
}
.grid-card-img-wrap {
  position: relative; height: 220rpx; overflow: hidden;
}
.grid-card-img { width: 100%; height: 100%; }
.grid-card-img-placeholder {
  background: linear-gradient(135deg, #d6d3d1, #a8a29e);
}
.grid-status-badge {
  position: absolute; top: 12rpx; left: 12rpx;
  background: rgba(0,0,0,0.6); border-radius: 9999rpx;
  padding: 6rpx 16rpx; backdrop-filter: blur(4px);
}
.grid-badge-text { font-size: 20rpx; color: #fff; font-weight: 600; }

.grid-card-info { padding: 16rpx 20rpx 12rpx; }
.grid-card-name {
  font-size: 28rpx; font-weight: 700; color: #1c1917;
  display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.grid-card-row {
  display: flex; align-items: center; gap: 12rpx;
  margin-top: 6rpx;
}
.grid-card-rating { font-size: 24rpx; font-weight: 600; color: #c2410c; }
.grid-card-price { font-size: 24rpx; font-weight: 600; color: #78716c; }
.grid-card-tags {
  display: flex; flex-wrap: wrap; gap: 8rpx; margin-top: 8rpx;
}
.grid-tag {
  font-size: 20rpx; font-weight: 500; color: #78716c;
  background: #f5f5f4; border-radius: 9999rpx;
  padding: 4rpx 14rpx;
}

.grid-card-actions {
  display: flex; border-top: 1rpx solid #f0efee;
}
.grid-action {
  flex: 1; text-align: center; padding: 16rpx 0;
}
.grid-action:active { background: #f5f5f4; }
.grid-action:first-child { border-right: 1rpx solid #f0efee; }
.grid-action-text { font-size: 24rpx; font-weight: 600; color: #78716c; }
.grid-action-text-danger { font-size: 24rpx; font-weight: 600; color: #dc2626; }

/* ---- Empty ---- */
.empty-card {
  background: #ffffff; border-radius: 64rpx;
  padding: 80rpx 40rpx; text-align: center;
  box-shadow: 0 12rpx 32rpx rgba(0,0,0,0.06);
}
.empty-icon { font-size: 72rpx; display: block; margin-bottom: 20rpx; }
.empty-title {
  font-size: 30rpx; font-weight: 700; color: #1c1917;
  display: block; margin-bottom: 8rpx;
}
.empty-desc { font-size: 24rpx; color: #a8a29e; display: block; }
</style>

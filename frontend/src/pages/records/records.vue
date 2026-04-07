<template>
  <view class="page">
    <!-- Header — Figma 美食足迹 -->
    <view class="header-section">
      <view class="header-top">
        <text class="header-title">美食足迹</text>
        <view class="count-badge" v-if="records.length">
          <text class="count-badge-text">{{ records.length }} 次到访</text>
        </view>
      </view>
      <text class="header-desc">记录每一次美味邂逅</text>
    </view>

    <!-- Bento Hero — Stats Overview -->
    <view class="hero-row" v-if="records.length > 0">
      <view class="hero-highlight">
        <view class="highlight-gradient"></view>
        <view class="highlight-content">
          <text class="highlight-eyebrow">✨ 美食之旅</text>
          <text class="highlight-num">{{ records.length }}</text>
          <text class="highlight-label">次探店记录</text>
        </view>
      </view>
      <view class="hero-stat-stack">
        <view class="hero-stat-card">
          <text class="hero-stat-icon">💰</text>
          <text class="hero-stat-val">¥{{ totalCost }}</text>
          <text class="hero-stat-label">总花费</text>
        </view>
        <view class="hero-stat-card">
          <text class="hero-stat-icon">⭐</text>
          <text class="hero-stat-val">{{ avgRating }}</text>
          <text class="hero-stat-label">平均评分</text>
        </view>
      </view>
    </view>

    <!-- Timeline — Figma alternating cards -->
    <view class="timeline" v-if="records.length > 0">
      <view class="timeline-line"></view>
      <view
        v-for="(rec, idx) in records"
        :key="rec.id"
        :class="['timeline-entry', idx % 2 === 0 ? 'entry-left' : 'entry-right']"
      >
        <view class="timeline-dot"></view>
        <view class="entry-card">
          <view class="entry-card-header">
            <text class="entry-name">{{ rec.restaurant_name }}</text>
            <text class="entry-date">{{ formatDate(rec.dining_date) }}</text>
          </view>
          <view class="entry-metrics" v-if="rec.actual_cost || rec.rating">
            <view class="entry-metric" v-if="rec.actual_cost">
              <text class="metric-val metric-cost">¥{{ rec.actual_cost }}</text>
              <text class="metric-label">消费</text>
            </view>
            <view class="entry-metric" v-if="rec.rating">
              <view class="star-row">
                <text
                  v-for="s in 5"
                  :key="s"
                  :class="['star', s <= Math.round(rec.rating) ? 'star-filled' : '']"
                >★</text>
              </view>
              <text class="metric-label">{{ rec.rating }}分</text>
            </view>
          </view>
          <text class="entry-address" v-if="rec.departure_address">📍 {{ rec.departure_address }}</text>
          <view class="entry-comment-wrap" v-if="rec.comment">
            <text class="entry-comment">{{ rec.comment }}</text>
          </view>
          <view class="entry-actions">
            <view class="entry-delete" @click="confirmDelete(rec)">
              <text class="entry-delete-text">删除</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Empty State -->
    <view v-if="records.length === 0" class="empty-card">
      <text class="empty-icon">🗺</text>
      <text class="empty-title">还没有美食足迹</text>
      <text class="empty-desc">在「选餐厅」页面开始你的美食之旅</text>
    </view>

    <!-- FAB — Quick Log Button (Figma floating) -->
    <view class="fab" @click="goAdd" v-if="records.length > 0">
      <text class="fab-text">+</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { recordApi, checkAuthGate } from '../../api'

const records = ref([])

const totalCost = computed(() => {
  return records.value.reduce((sum, r) => sum + (r.actual_cost || 0), 0)
})

const avgRating = computed(() => {
  const rated = records.value.filter(r => r.rating)
  if (!rated.length) return '--'
  return (rated.reduce((sum, r) => sum + r.rating, 0) / rated.length).toFixed(1)
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  if (parts.length >= 3) return `${parts[1]}/${parts[2]}`
  return dateStr
}

const fetchRecords = async () => {
  records.value = await recordApi.list()
}

const confirmDelete = (rec) => {
  uni.showModal({
    title: '确认删除',
    content: '确定删除这条记录吗？',
    success: async (res) => {
      if (res.confirm) {
        await recordApi.remove(rec.id)
        uni.showToast({ title: '已删除' })
        fetchRecords()
      }
    }
  })
}

const goAdd = () => {
  uni.navigateTo({ url: '/pages/records/add' })
}

onShow(async () => {
  if (!(await checkAuthGate())) return
  fetchRecords()
})
</script>

<style scoped>
.page {
  padding: 40rpx 32rpx 160rpx;
  min-height: 100vh;
  background: #f7f6f5;
}

/* ---- Header ---- */
.header-section { margin-bottom: 32rpx; }
.header-top { display: flex; align-items: center; gap: 16rpx; margin-bottom: 8rpx; }
.header-title {
  font-size: 52rpx; font-weight: 900; color: #1c1917;
  letter-spacing: -2rpx;
}
.count-badge {
  background: #ffedd5; border-radius: 9999rpx;
  padding: 8rpx 20rpx;
}
.count-badge-text { font-size: 22rpx; font-weight: 700; color: #9a3412; }
.header-desc { font-size: 26rpx; color: #78716c; display: block; }

/* ---- Hero Row ---- */
.hero-row { display: flex; gap: 16rpx; margin-bottom: 40rpx; }
.hero-highlight {
  flex: 1.2; position: relative; border-radius: 64rpx;
  overflow: hidden; padding: 32rpx 28rpx; min-height: 200rpx;
  background: linear-gradient(135deg, #9b3f00, #ff7a2c);
}
.highlight-gradient {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.15));
}
.highlight-content { position: relative; z-index: 1; }
.highlight-eyebrow {
  display: block; font-size: 22rpx; color: rgba(255,255,255,0.8);
  font-weight: 600; margin-bottom: 8rpx;
}
.highlight-num {
  display: block; font-size: 72rpx; font-weight: 900; color: #fff;
  line-height: 1;
}
.highlight-label { display: block; font-size: 24rpx; color: rgba(255,255,255,0.75); margin-top: 4rpx; }

.hero-stat-stack {
  flex: 1; display: flex; flex-direction: column; gap: 16rpx;
}
.hero-stat-card {
  background: #ffffff; border-radius: 48rpx;
  padding: 20rpx 24rpx; flex: 1;
  display: flex; align-items: center; gap: 12rpx;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.04);
}
.hero-stat-icon { font-size: 32rpx; }
.hero-stat-val { font-size: 28rpx; font-weight: 800; color: #1c1917; }
.hero-stat-label { font-size: 20rpx; color: #a8a29e; }

/* ---- Timeline ---- */
.timeline { position: relative; padding-left: 40rpx; }
.timeline-line {
  position: absolute; left: 18rpx; top: 0; bottom: 0;
  width: 4rpx; background: linear-gradient(to bottom, #9b3f00, #ff7a2c, #e2e2e1);
  border-radius: 2rpx;
}
.timeline-entry { position: relative; margin-bottom: 24rpx; }
.timeline-dot {
  position: absolute; left: -32rpx; top: 28rpx;
  width: 20rpx; height: 20rpx; border-radius: 50%;
  background: #9b3f00; border: 4rpx solid #f7f6f5;
  z-index: 2;
}

/* Entry Card */
.entry-card {
  background: #ffffff; border-radius: 48rpx;
  padding: 28rpx 28rpx 20rpx;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.04);
  border: 1rpx solid rgba(173,173,172,0.08);
}
.entry-card-header {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 12rpx;
}
.entry-name { font-size: 32rpx; font-weight: 800; color: #1c1917; }
.entry-date { font-size: 24rpx; color: #a8a29e; font-weight: 500; }

.entry-metrics { display: flex; gap: 32rpx; margin-bottom: 12rpx; }
.entry-metric { display: flex; flex-direction: column; }
.metric-val { font-size: 30rpx; font-weight: 700; line-height: 1.2; }
.metric-cost { color: #9b3f00; }
.metric-label { font-size: 20rpx; color: #a8a29e; margin-top: 2rpx; }

.star-row { display: flex; gap: 2rpx; }
.star { font-size: 24rpx; color: #d6d3d1; }
.star-filled { color: #f59e0b; }

.entry-address {
  font-size: 24rpx; color: #78716c; display: block; margin-bottom: 8rpx;
}
.entry-comment-wrap {
  background: #f5f5f4; border-radius: 24rpx;
  padding: 16rpx 20rpx; margin-top: 8rpx;
  border-left: 6rpx solid #9b3f00;
}
.entry-comment { font-size: 26rpx; color: #57534e; line-height: 1.5; }

.entry-actions {
  display: flex; justify-content: flex-end;
  margin-top: 12rpx; padding-top: 12rpx;
  border-top: 1rpx solid #f0efee;
}
.entry-delete { padding: 8rpx 20rpx; }
.entry-delete-text { font-size: 24rpx; color: #dc2626; font-weight: 600; }

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

/* ---- FAB ---- */
.fab {
  position: fixed; right: 40rpx; bottom: 160rpx;
  width: 96rpx; height: 96rpx; border-radius: 50%;
  background: linear-gradient(135deg, #9b3f00, #ff7a2c);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 16rpx 48rpx rgba(155,63,0,0.35);
  z-index: 100;
}
.fab:active { transform: scale(0.92); }
.fab-text { font-size: 48rpx; color: #fff; font-weight: 300; line-height: 1; margin-top: -4rpx; }
</style>

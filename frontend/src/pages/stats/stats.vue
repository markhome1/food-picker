<template>
  <view class="page">
    <!-- Header — Figma 美食报表 -->
    <view class="header-section">
      <text class="header-title">美食报表</text>
      <view class="period-toggle">
        <view :class="['toggle-btn', period === 'all' ? 'toggle-active' : '']" @click="period = 'all'">
          <text :class="['toggle-text', period === 'all' ? 'toggle-text-active' : '']">全部</text>
        </view>
        <view :class="['toggle-btn', period === 'month' ? 'toggle-active' : '']" @click="period = 'month'">
          <text :class="['toggle-text', period === 'month' ? 'toggle-text-active' : '']">本月</text>
        </view>
      </view>
    </view>

    <view v-if="spaceInvite && spaceInvite.join_code" class="invite-card">
      <text class="invite-card-title">邀请伙伴加入空间</text>
      <text class="invite-card-sub">把邀请码发给对方，在「登录 → 加入空间」里填写</text>
      <view class="invite-code-row">
        <text class="invite-code-value" selectable>{{ spaceInvite.join_code }}</text>
        <view class="invite-copy-btn" @click="copyJoinCode">
          <text class="invite-copy-btn-t">复制</text>
        </view>
      </view>
      <text v-if="spaceInvite.max_members != null" class="invite-meta">
        当前 {{ spaceInvite.member_count || 0 }} / {{ spaceInvite.max_members }} 人
      </text>
    </view>

    <view v-if="stats" class="bento-grid">
      <!-- Favorite Spot — Wide Card (Figma gradient bg + stats) -->
      <view class="bento-wide" v-if="topRestaurant">
        <view class="fav-card">
          <view class="fav-gradient"></view>
          <view class="fav-content">
            <text class="fav-eyebrow">🏆 最爱餐厅</text>
            <text class="fav-name">{{ topRestaurant.name }}</text>
            <view class="fav-stats">
              <view class="fav-stat">
                <text class="fav-stat-num">{{ topRestaurant.visits }}</text>
                <text class="fav-stat-label">次到访</text>
              </view>
              <view class="fav-stat">
                <text class="fav-stat-num">Top 1</text>
                <text class="fav-stat-label">排名</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- Spending Overview — Square Card -->
      <view class="bento-row">
        <view class="bento-square">
          <view class="spend-card">
            <text class="spend-label">总消费</text>
            <text class="spend-amount">¥{{ stats.total_cost || 0 }}</text>
            <view class="spend-ring">
              <view class="ring-outer">
                <view class="ring-inner">
                  <text class="ring-count">{{ stats.total_count || 0 }}</text>
                  <text class="ring-unit">次</text>
                </view>
              </view>
            </view>
          </view>
        </view>

        <!-- Quick Stats — Small Cards Stack -->
        <view class="bento-stack">
          <view class="mini-card">
            <text class="mini-icon">🍽</text>
            <view class="mini-info">
              <text class="mini-num">{{ stats.total_count || 0 }}</text>
              <text class="mini-label">就餐次数</text>
            </view>
          </view>
          <view class="mini-card">
            <text class="mini-icon">💰</text>
            <view class="mini-info">
              <text class="mini-num">¥{{ avgCost }}</text>
              <text class="mini-label">平均消费</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Favorite Cuisines — Bar Chart Card (Figma) -->
      <view class="bento-chart-card" v-if="stats.restaurant_visits && stats.restaurant_visits.length">
        <text class="chart-title">餐厅排行 🏅</text>
        <view class="bar-chart">
          <view
            v-for="(item, idx) in stats.restaurant_visits.slice(0, 5)"
            :key="item.name"
            class="bar-row"
          >
            <view class="bar-rank-wrap">
              <text :class="['bar-rank', idx < 3 ? 'bar-rank-top' : '']">{{ idx + 1 }}</text>
            </view>
            <text class="bar-label">{{ item.name }}</text>
            <view class="bar-track">
              <view
                class="bar-fill"
                :style="{ width: rankBarWidth(item.visits) }"
              ></view>
            </view>
            <text class="bar-count">{{ item.visits }}次</text>
          </view>
        </view>
      </view>

      <!-- Monthly Trend — Medium Card (Figma heatmap-inspired) -->
      <view class="bento-chart-card" v-if="stats.monthly && stats.monthly.length">
        <text class="chart-title">月度趋势 📈</text>
        <view class="monthly-chart">
          <view
            v-for="m in stats.monthly"
            :key="m.month"
            class="month-row"
          >
            <text class="month-label">{{ m.month }}</text>
            <view class="month-bar-track">
              <view class="month-bar-fill" :style="{ width: barWidth(m.count) }"></view>
            </view>
            <view class="month-info">
              <text class="month-count">{{ m.count }}次</text>
              <text class="month-cost">¥{{ m.total_cost }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Loading State -->
    <view v-if="!stats" class="loading-wrap">
      <view class="loading-spinner"></view>
      <text class="loading-text">加载中...</text>
    </view>

    <view v-if="hasToken" class="logout-row">
      <text class="logout-link" @click="logout">退出登录</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { recordApi, authApi, clearAuthToken, checkAuthGate } from '../../api'

const stats = ref(null)
const hasToken = ref(false)
const spaceInvite = ref(null)
const maxCount = ref(1)
const maxVisits = ref(1)
const period = ref('all')

const fetchStats = async () => {
  const res = await recordApi.stats({ period: period.value })
  stats.value = res.data
  if (stats.value && stats.value.monthly && stats.value.monthly.length) {
    maxCount.value = Math.max(...stats.value.monthly.map(m => m.count), 1)
  }
  if (stats.value && stats.value.restaurant_visits && stats.value.restaurant_visits.length) {
    maxVisits.value = Math.max(...stats.value.restaurant_visits.map(r => r.visits), 1)
  }
}

const topRestaurant = computed(() => {
  if (!stats.value || !stats.value.restaurant_visits || !stats.value.restaurant_visits.length) return null
  return stats.value.restaurant_visits[0]
})

const avgCost = computed(() => {
  if (!stats.value || !stats.value.total_count || !stats.value.total_cost) return '0'
  return Math.round(stats.value.total_cost / stats.value.total_count)
})

const barWidth = (count) => {
  return Math.max(10, (count / maxCount.value) * 100) + '%'
}

const rankBarWidth = (visits) => {
  return Math.max(10, (visits / maxVisits.value) * 100) + '%'
}

const logout = () => {
  clearAuthToken()
  uni.reLaunch({ url: '/pages/login/login' })
}

const fetchSpaceInvite = async () => {
  spaceInvite.value = null
  if (!uni.getStorageSync('auth_token')) return
  try {
    const res = await authApi.me()
    if (res.auth_required && res.join_code) {
      spaceInvite.value = {
        join_code: res.join_code,
        member_count: res.member_count,
        max_members: res.max_members,
      }
    }
  } catch {
    spaceInvite.value = null
  }
}

const copyJoinCode = () => {
  const code = spaceInvite.value && spaceInvite.value.join_code
  if (!code) return
  uni.setClipboardData({
    data: code,
    success: () => uni.showToast({ title: '邀请码已复制', icon: 'none' }),
  })
}

onShow(async () => {
  if (!(await checkAuthGate())) return
  hasToken.value = !!uni.getStorageSync('auth_token')
  await fetchSpaceInvite()
  fetchStats()
})
watch(period, () => fetchStats())
</script>

<style scoped>
.page {
  padding: 40rpx 32rpx 120rpx;
  min-height: 100vh;
  background: #f7f6f5;
}

.logout-row {
  margin-top: 48rpx;
  padding-bottom: 48rpx;
  align-items: center;
  justify-content: center;
  display: flex;
}
.logout-link {
  font-size: 26rpx;
  color: #a8a29e;
  text-decoration: underline;
}

/* ---- Header ---- */
.header-section {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 32rpx;
}
.header-title {
  font-size: 52rpx; font-weight: 900; color: #1c1917;
  letter-spacing: -2rpx;
}
.period-toggle {
  display: flex; background: #e2e2e1;
  border-radius: 9999rpx; padding: 4rpx;
}
.toggle-btn {
  padding: 12rpx 28rpx; border-radius: 9999rpx;
}
.toggle-active { background: #ffffff; box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.08); }
.toggle-text { font-size: 24rpx; font-weight: 600; color: #78716c; }
.toggle-text-active { color: #1c1917; }

/* ---- 邀请码 ---- */
.invite-card {
  background: #ffffff;
  border-radius: 40rpx;
  padding: 28rpx 28rpx 24rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid #e7e5e4;
  box-shadow: 0 8rpx 24rpx rgba(124, 45, 18, 0.06);
}
.invite-card-title {
  display: block;
  font-size: 30rpx;
  font-weight: 800;
  color: #1c1917;
}
.invite-card-sub {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #a8a29e;
  line-height: 1.45;
}
.invite-code-row {
  margin-top: 20rpx;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16rpx;
}
.invite-code-value {
  flex: 1;
  min-width: 0;
  font-size: 34rpx;
  font-weight: 800;
  color: #9b3f00;
  letter-spacing: 2rpx;
}
.invite-copy-btn {
  flex-shrink: 0;
  padding: 16rpx 32rpx;
  border-radius: 9999rpx;
  background: linear-gradient(90deg, #9b3f00, #ff7a2c);
}
.invite-copy-btn-t {
  font-size: 26rpx;
  font-weight: 700;
  color: #ffffff;
}
.invite-meta {
  display: block;
  margin-top: 16rpx;
  font-size: 22rpx;
  color: #78716c;
}

/* ---- Bento Grid ---- */
.bento-grid { display: flex; flex-direction: column; gap: 20rpx; }

/* Wide card — Favorite Spot */
.bento-wide { width: 100%; }
.fav-card {
  position: relative; border-radius: 64rpx; overflow: hidden;
  padding: 40rpx 36rpx; min-height: 260rpx;
  background: linear-gradient(135deg, #9b3f00, #ff7a2c);
}
.fav-gradient {
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(0,0,0,0.1), transparent 60%);
}
.fav-content { position: relative; z-index: 1; }
.fav-eyebrow {
  display: block; font-size: 24rpx; color: rgba(255,255,255,0.85);
  font-weight: 600; margin-bottom: 12rpx; letter-spacing: 2rpx;
}
.fav-name {
  display: block; font-size: 52rpx; font-weight: 900; color: #ffffff;
  letter-spacing: -2rpx; line-height: 1.1; margin-bottom: 20rpx;
}
.fav-stats { display: flex; gap: 40rpx; }
.fav-stat { display: flex; flex-direction: column; }
.fav-stat-num { font-size: 36rpx; font-weight: 800; color: #fff; }
.fav-stat-label { font-size: 22rpx; color: rgba(255,255,255,0.7); margin-top: 2rpx; }

/* Row layout for square + stack */
.bento-row { display: flex; gap: 20rpx; }

/* Spending square */
.bento-square { flex: 1; min-width: 0; }
.spend-card {
  background: #ffffff; border-radius: 64rpx;
  padding: 32rpx; height: 100%;
  box-shadow: 0 12rpx 32rpx rgba(0,0,0,0.06);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.spend-label { font-size: 22rpx; color: #a8a29e; font-weight: 600; letter-spacing: 2rpx; }
.spend-amount {
  font-size: 48rpx; font-weight: 900; color: #9b3f00;
  margin: 8rpx 0;
}
.spend-ring { margin-top: 8rpx; }
.ring-outer {
  width: 120rpx; height: 120rpx; border-radius: 50%;
  background: conic-gradient(#9b3f00 0%, #ff7a2c 70%, #e2e2e1 70%);
  display: flex; align-items: center; justify-content: center;
}
.ring-inner {
  width: 88rpx; height: 88rpx; border-radius: 50%;
  background: #ffffff; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.ring-count { font-size: 28rpx; font-weight: 800; color: #1c1917; line-height: 1; }
.ring-unit { font-size: 18rpx; color: #a8a29e; }

/* Small cards stack */
.bento-stack {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 20rpx;
}
.mini-card {
  background: #ffffff; border-radius: 48rpx;
  padding: 24rpx 28rpx; flex: 1;
  display: flex; align-items: center; gap: 16rpx;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.04);
}
.mini-icon { font-size: 40rpx; }
.mini-info { display: flex; flex-direction: column; }
.mini-num { font-size: 32rpx; font-weight: 800; color: #1c1917; line-height: 1.2; }
.mini-label { font-size: 20rpx; color: #a8a29e; margin-top: 2rpx; }

/* ---- Chart Cards ---- */
.bento-chart-card {
  background: #ffffff; border-radius: 64rpx;
  padding: 32rpx 28rpx;
  box-shadow: 0 12rpx 32rpx rgba(0,0,0,0.06);
}
.chart-title {
  display: block; font-size: 30rpx; font-weight: 800;
  color: #1c1917; margin-bottom: 24rpx;
}

/* Bar chart */
.bar-chart { display: flex; flex-direction: column; gap: 16rpx; }
.bar-row { display: flex; align-items: center; gap: 12rpx; }
.bar-rank-wrap { width: 40rpx; flex-shrink: 0; }
.bar-rank {
  font-size: 24rpx; font-weight: 700; color: #a8a29e;
  text-align: center; display: block;
}
.bar-rank-top { color: #9b3f00; }
.bar-label {
  font-size: 26rpx; font-weight: 600; color: #44403c;
  min-width: 120rpx; flex-shrink: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bar-track {
  flex: 1; height: 24rpx; background: #f5f5f4;
  border-radius: 9999rpx; overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 9999rpx;
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  transition: width 0.4s ease;
}
.bar-count {
  font-size: 22rpx; font-weight: 600; color: #a8a29e;
  min-width: 60rpx; text-align: right; flex-shrink: 0;
}

/* Monthly chart */
.monthly-chart { display: flex; flex-direction: column; gap: 18rpx; }
.month-row { display: flex; align-items: center; gap: 12rpx; }
.month-label {
  width: 100rpx; font-size: 24rpx; color: #78716c; font-weight: 500;
  flex-shrink: 0;
}
.month-bar-track {
  flex: 1; height: 28rpx; background: #f5f5f4;
  border-radius: 9999rpx; overflow: hidden;
}
.month-bar-fill {
  height: 100%; border-radius: 9999rpx;
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  transition: width 0.4s ease;
}
.month-info { flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; }
.month-count { font-size: 22rpx; font-weight: 700; color: #1c1917; }
.month-cost { font-size: 20rpx; color: #a8a29e; }

/* ---- Loading ---- */
.loading-wrap { text-align: center; padding: 120rpx 0; }
.loading-spinner {
  width: 48rpx; height: 48rpx; border-radius: 50%;
  border: 4rpx solid #e2e2e1;
  border-top-color: #9b3f00;
  animation: spin 0.8s linear infinite; margin: 0 auto 16rpx;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-size: 24rpx; color: #a8a29e; }
</style>

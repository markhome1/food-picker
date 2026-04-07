<template>
  <view class="page">
    <!-- Header -->
    <view class="header-section">
      <text class="header-title">记录美食</text>
      <text class="header-desc">留下这一刻的美味记忆</text>
    </view>

    <!-- Restaurant Name Card -->
    <view class="restaurant-card">
      <text class="restaurant-eyebrow">餐厅</text>
      <text class="restaurant-name">{{ restaurantName || '选择餐厅' }}</text>
    </view>

    <!-- Photo Upload Area — Figma style -->
    <view class="photo-section">
      <view class="photo-area">
        <text class="photo-icon">📷</text>
        <text class="photo-hint">拍照记录美食</text>
        <text class="photo-sub">点击上传照片（开发中）</text>
      </view>
    </view>

    <!-- Form Card -->
    <view class="form-card">
      <!-- Location Input with map icon -->
      <view class="form-field">
        <view class="field-label-row">
          <text class="field-icon">📍</text>
          <text class="field-label">出发地</text>
        </view>
        <input class="field-input" v-model="form.departure_address" placeholder="如: 天府广场、公司" />
      </view>

      <!-- Date Picker -->
      <view class="form-field">
        <view class="field-label-row">
          <text class="field-icon">📅</text>
          <text class="field-label">就餐日期</text>
        </view>
        <picker mode="date" :value="form.dining_date" @change="onDateChange">
          <view class="field-input field-input-picker">{{ form.dining_date }}</view>
        </picker>
      </view>

      <!-- Cost Input -->
      <view class="form-field">
        <view class="field-label-row">
          <text class="field-icon">💰</text>
          <text class="field-label">实际消费</text>
        </view>
        <input class="field-input" type="digit" v-model="form.actual_cost" placeholder="¥ 金额" />
      </view>

      <!-- Star Rating — Figma 5 interactive stars -->
      <view class="form-field">
        <view class="field-label-row">
          <text class="field-icon">⭐</text>
          <text class="field-label">评分</text>
        </view>
        <view class="star-rating">
          <view
            v-for="s in 5"
            :key="s"
            class="star-btn"
            @click="setRating(s)"
          >
            <text :class="['star-char', s <= selectedRating ? 'star-active' : '']">★</text>
          </view>
          <text class="rating-display" v-if="selectedRating">{{ selectedRating }}.0</text>
        </view>
      </view>

      <!-- Notes Textarea -->
      <view class="form-field">
        <view class="field-label-row">
          <text class="field-icon">📝</text>
          <text class="field-label">备注</text>
        </view>
        <textarea class="field-textarea" v-model="form.comment" placeholder="味道如何？推荐菜品？留下你的美食笔记..." />
      </view>

      <!-- Memory Tags — Figma chips -->
      <view class="form-field">
        <view class="field-label-row">
          <text class="field-icon">🏷</text>
          <text class="field-label">记忆标签</text>
        </view>
        <view class="tag-chips">
          <view
            v-for="tag in availableTags"
            :key="tag"
            :class="['tag-chip', selectedTags.includes(tag) ? 'tag-chip-active' : '']"
            @click="toggleTag(tag)"
          >
            <text :class="['tag-chip-text', selectedTags.includes(tag) ? 'tag-chip-text-active' : '']">{{ tag }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- Action Buttons — Figma Submit + Cancel -->
    <view class="action-section">
      <view class="btn-submit" @click="save">
        <text class="btn-submit-text">记录这一顿 ✨</text>
      </view>
      <view class="btn-cancel" @click="goBack">
        <text class="btn-cancel-text">取消</text>
      </view>
    </view>

    <!-- Decorative floating elements -->
    <view class="deco-circle deco-1"></view>
    <view class="deco-circle deco-2"></view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { recordApi } from '../../api'

const restaurantId = ref(0)
const restaurantName = ref('')
const selectedRating = ref(0)
const selectedTags = ref([])
const today = new Date().toISOString().split('T')[0]

const availableTags = ['约会', '聚餐', '独食', '打卡', '庆祝', '日常', '出差', '旅行']

const form = ref({
  dining_date: today,
  departure_address: '',
  actual_cost: '',
  comment: '',
})

const onDateChange = (e) => {
  form.value.dining_date = e.detail.value
}

const setRating = (val) => {
  selectedRating.value = selectedRating.value === val ? 0 : val
}

const toggleTag = (tag) => {
  const idx = selectedTags.value.indexOf(tag)
  if (idx >= 0) {
    selectedTags.value.splice(idx, 1)
  } else {
    selectedTags.value.push(tag)
  }
}

const save = async () => {
  const data = {
    restaurant_id: restaurantId.value,
    dining_date: form.value.dining_date,
    departure_address: form.value.departure_address,
    comment: form.value.comment,
  }
  if (form.value.actual_cost) data.actual_cost = parseFloat(form.value.actual_cost)
  if (selectedRating.value) data.rating = selectedRating.value
  if (selectedTags.value.length > 0) {
    data.comment = (data.comment ? data.comment + ' ' : '') + selectedTags.value.map(t => '#' + t).join(' ')
  }

  try {
    await recordApi.create(data)
    uni.showToast({ title: '已记录！' })
    setTimeout(() => uni.navigateBack(), 500)
  } catch (e) {
    console.error(e)
  }
}

const goBack = () => {
  uni.navigateBack()
}

onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  const options = currentPage.$page ? currentPage.$page.options : currentPage.options
  if (options) {
    restaurantId.value = parseInt(options.restaurant_id || 0)
    restaurantName.value = decodeURIComponent(options.restaurant_name || '')
  }
})
</script>

<style scoped>
.page {
  padding: 40rpx 32rpx 120rpx;
  min-height: 100vh;
  background: #f7f6f5;
  position: relative; overflow: hidden;
}

/* ---- Header ---- */
.header-section { margin-bottom: 28rpx; }
.header-title {
  display: block; font-size: 48rpx; font-weight: 900;
  color: #1c1917; letter-spacing: -2rpx;
}
.header-desc {
  display: block; font-size: 26rpx; color: #78716c; margin-top: 6rpx;
}

/* ---- Restaurant Card ---- */
.restaurant-card {
  background: linear-gradient(135deg, #9b3f00, #ff7a2c);
  border-radius: 48rpx; padding: 28rpx 32rpx;
  margin-bottom: 20rpx;
}
.restaurant-eyebrow {
  display: block; font-size: 22rpx; color: rgba(255,255,255,0.75);
  font-weight: 600; margin-bottom: 4rpx;
}
.restaurant-name {
  display: block; font-size: 40rpx; font-weight: 900; color: #fff;
}

/* ---- Photo Section ---- */
.photo-section { margin-bottom: 20rpx; }
.photo-area {
  background: #ffffff; border-radius: 48rpx;
  padding: 48rpx 32rpx; text-align: center;
  border: 3rpx dashed #d6d3d1;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.03);
}
.photo-icon { font-size: 64rpx; display: block; margin-bottom: 12rpx; }
.photo-hint { display: block; font-size: 28rpx; font-weight: 700; color: #44403c; }
.photo-sub { display: block; font-size: 22rpx; color: #a8a29e; margin-top: 6rpx; }

/* ---- Form Card ---- */
.form-card {
  background: #ffffff; border-radius: 64rpx;
  padding: 32rpx 28rpx;
  box-shadow: 0 12rpx 32rpx rgba(0,0,0,0.06);
  margin-bottom: 28rpx;
}
.form-field { margin-bottom: 28rpx; }
.form-field:last-child { margin-bottom: 0; }
.field-label-row {
  display: flex; align-items: center; gap: 8rpx;
  margin-bottom: 12rpx;
}
.field-icon { font-size: 28rpx; }
.field-label {
  font-size: 24rpx; font-weight: 700; color: #57534e;
  letter-spacing: 1rpx;
}
.field-input {
  background: #f5f5f4; border-radius: 32rpx;
  padding: 22rpx 28rpx; font-size: 28rpx; color: #1c1917;
  border: 1rpx solid #e7e5e4; width: 100%;
}
.field-input-picker {
  display: flex; align-items: center;
}
.field-textarea {
  background: #f5f5f4; border-radius: 32rpx;
  padding: 22rpx 28rpx; font-size: 28rpx;
  height: 200rpx; color: #1c1917;
  border: 1rpx solid #e7e5e4; width: 100%;
  line-height: 1.6;
}

/* Star Rating */
.star-rating {
  display: flex; align-items: center; gap: 8rpx;
}
.star-btn { padding: 8rpx; }
.star-char { font-size: 48rpx; color: #d6d3d1; transition: color 0.2s; }
.star-active { color: #f59e0b; }
.rating-display {
  font-size: 28rpx; font-weight: 700; color: #f59e0b;
  margin-left: 12rpx;
}

/* Tag Chips */
.tag-chips { display: flex; flex-wrap: wrap; gap: 12rpx; }
.tag-chip {
  padding: 12rpx 24rpx; border-radius: 9999rpx;
  background: #f5f5f4; border: 1rpx solid #e7e5e4;
}
.tag-chip-active {
  background: #ffedd5; border-color: #fed7aa;
}
.tag-chip-text { font-size: 24rpx; font-weight: 500; color: #57534e; }
.tag-chip-text-active { color: #9a3412; font-weight: 600; }

/* ---- Actions ---- */
.action-section { display: flex; flex-direction: column; gap: 16rpx; }
.btn-submit {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  border-radius: 9999rpx; padding: 30rpx;
  text-align: center;
  box-shadow: 0 20rpx 60rpx rgba(155,63,0,0.3);
}
.btn-submit:active { opacity: 0.92; transform: scale(0.98); }
.btn-submit-text { font-size: 32rpx; font-weight: 800; color: #fff; }
.btn-cancel {
  background: #e2e2e1; border-radius: 9999rpx;
  padding: 26rpx; text-align: center;
}
.btn-cancel:active { background: #d6d3d1; }
.btn-cancel-text { font-size: 28rpx; font-weight: 600; color: #57534e; }

/* ---- Decorative ---- */
.deco-circle {
  position: absolute; border-radius: 50%;
  pointer-events: none; opacity: 0.06;
}
.deco-1 {
  width: 300rpx; height: 300rpx;
  background: #9b3f00; top: -80rpx; right: -60rpx;
}
.deco-2 {
  width: 200rpx; height: 200rpx;
  background: #ff7a2c; bottom: 100rpx; left: -50rpx;
}
</style>

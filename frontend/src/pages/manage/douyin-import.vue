<template>
  <view class="page">
    <text class="hint">
      粘贴抖音分享链接（含 v.douyin.com 或 www.douyin.com）。服务端会尝试抓取标题并走高德 POI，写入「自己精选」。若抖音页面无标题（动态加载），请改用截图识别。
    </text>
    <textarea
      class="ta"
      v-model="url"
      placeholder="长按抖音分享 → 复制链接 → 粘贴到这里"
      :auto-height="true"
    />
    <view class="btn" @click="submit"><text class="btn-t">解析并加入自己精选</text></view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { importApi } from '../../api'

const url = ref('')

const submit = async () => {
  const u = url.value.trim()
  if (!u) {
    uni.showToast({ title: '请先粘贴链接', icon: 'none' })
    return
  }
  uni.showLoading({ title: '解析中…', mask: true })
  try {
    const res = await importApi.douyin(u)
    uni.showToast({
      title: res.merged ? '已合并进自己精选' : '已加入自己精选',
      icon: 'success',
    })
    setTimeout(() => uni.navigateBack(), 500)
  } catch (_) {
    /* request 已 toast detail */
  } finally {
    uni.hideLoading()
  }
}
</script>

<style scoped>
.page {
  padding: 32rpx;
  min-height: 100vh;
  background: #f7f6f5;
}
.hint {
  display: block;
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.55;
  margin-bottom: 24rpx;
}
.ta {
  width: 100%;
  min-height: 200rpx;
  box-sizing: border-box;
  padding: 24rpx;
  background: #fff;
  border-radius: 24rpx;
  border: 1rpx solid #e7e5e4;
  font-size: 26rpx;
  color: #1c1917;
  margin-bottom: 32rpx;
}
.btn {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  border-radius: 9999rpx;
  padding: 28rpx;
  text-align: center;
}
.btn-t {
  font-size: 30rpx;
  font-weight: 700;
  color: #fff;
}
</style>

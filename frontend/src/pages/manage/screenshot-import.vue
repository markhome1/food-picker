<template>
  <view class="page">
    <text class="hint">
      上传探店截图，自动识别文字后列出候选店名；点选一家即走高德检索并加入「自己精选」。需在 backend/.env 配置 OCR_SPACE_API_KEY（见 ocr.space 免费注册）。
    </text>

    <view class="pick" @click="pickImage">
      <text class="pick-t">{{ imagePath ? '已选图，点击重选' : '选择截图' }}</text>
    </view>

    <view class="btn" v-if="imagePath && !candidates.length" @click="runOcr">
      <text class="btn-t">识别文字</text>
    </view>

    <view v-if="candidates.length" class="sec">
      <text class="sec-title">点选一家店名</text>
      <view
        v-for="(c, i) in candidates"
        :key="i"
        class="cand"
        @click="pickCandidate(c)"
      >
        <text class="cand-t">{{ c }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { importApi, importOcrUpload } from '../../api'

const imagePath = ref('')
const candidates = ref([])

const pickImage = () => {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: (res) => {
      imagePath.value = res.tempFilePaths[0]
      candidates.value = []
    },
  })
}

const runOcr = async () => {
  if (!imagePath.value) return
  uni.showLoading({ title: '识别中…', mask: true })
  try {
    const res = await importOcrUpload(imagePath.value)
    if (res.code === 200 && res.candidates && res.candidates.length) {
      candidates.value = res.candidates
    } else {
      uni.showToast({ title: '未识别到店名，换张清晰截图', icon: 'none' })
    }
  } catch (_) {
    /* toast in upload */
  } finally {
    uni.hideLoading()
  }
}

const pickCandidate = async (name) => {
  uni.showLoading({ title: '添加中…', mask: true })
  try {
    await importApi.addByName(name, '')
    uni.showToast({ title: '已加入自己精选', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 500)
  } catch (_) {
    /* handled */
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
  padding-bottom: 120rpx;
}
.hint {
  display: block;
  font-size: 24rpx;
  color: #78716c;
  line-height: 1.55;
  margin-bottom: 28rpx;
}
.pick {
  padding: 36rpx;
  background: #fff;
  border-radius: 24rpx;
  border: 2rpx dashed #d6d3d1;
  text-align: center;
  margin-bottom: 24rpx;
}
.pick-t {
  font-size: 28rpx;
  color: #57534e;
  font-weight: 600;
}
.btn {
  background: linear-gradient(to right, #9b3f00, #ff7a2c);
  border-radius: 9999rpx;
  padding: 28rpx;
  text-align: center;
  margin-bottom: 32rpx;
}
.btn-t {
  font-size: 30rpx;
  font-weight: 700;
  color: #fff;
}
.sec-title {
  display: block;
  font-size: 28rpx;
  font-weight: 800;
  color: #1c1917;
  margin-bottom: 16rpx;
}
.cand {
  padding: 26rpx 28rpx;
  background: #fff;
  border-radius: 20rpx;
  margin-bottom: 12rpx;
  border: 1rpx solid #e7e5e4;
}
.cand:active {
  background: #fffaf5;
}
.cand-t {
  font-size: 28rpx;
  color: #44403c;
}
</style>

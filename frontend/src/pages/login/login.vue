<template>
  <view class="page">
    <view class="hero">
      <text class="hero-title">今天吃啥</text>
      <text class="hero-sub">情侣专属 · 最多两人共享同一空间</text>
    </view>

    <view class="tabs">
      <view
        v-for="t in tabList"
        :key="t.key"
        :class="['tab', mode === t.key ? 'tab-on' : '']"
        @click="mode = t.key"
      >
        <text :class="['tab-t', mode === t.key ? 'tab-t-on' : '']">{{ t.label }}</text>
      </view>
    </view>

    <view class="card">
      <template v-if="mode === 'login'">
        <view class="field">
          <text class="label">邮箱</text>
          <input class="input" v-model="loginEmail" type="text" placeholder="you@example.com" />
        </view>
        <view class="field">
          <text class="label">密码</text>
          <input class="input" v-model="loginPassword" password placeholder="至少 6 位" />
        </view>
        <button class="btn primary" :loading="loading" @click="doLogin">登录</button>
      </template>

      <template v-else-if="mode === 'register'">
        <view class="field">
          <text class="label">邮箱</text>
          <input class="input" v-model="regEmail" type="text" placeholder="第一人注册用" />
        </view>
        <view class="field">
          <text class="label">密码</text>
          <input class="input" v-model="regPassword" password placeholder="至少 6 位" />
        </view>
        <view class="field">
          <text class="label">昵称（可选）</text>
          <input class="input" v-model="regName" type="text" placeholder="怎么称呼你" />
        </view>
        <button class="btn primary" :loading="loading" @click="doRegister">创建情侣空间</button>
        <text class="hint">创建后会得到邀请码，把邀请码发给另一半用来注册第二人。</text>
      </template>

      <template v-else>
        <view class="field">
          <text class="label">邀请码</text>
          <input class="input" v-model="joinCode" type="text" placeholder="例如 ABC123-DEF456" />
        </view>
        <view class="field">
          <text class="label">邮箱</text>
          <input class="input" v-model="joinEmail" type="text" placeholder="第二人使用不同邮箱" />
        </view>
        <view class="field">
          <text class="label">密码</text>
          <input class="input" v-model="joinPassword" password placeholder="至少 6 位" />
        </view>
        <view class="field">
          <text class="label">昵称（可选）</text>
          <input class="input" v-model="joinName" type="text" placeholder="怎么称呼你" />
        </view>
        <button class="btn primary" :loading="loading" @click="doJoin">加入情侣空间</button>
        <text class="hint">每个空间仅 2 个账号；满员后无法再加入。</text>
      </template>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { authApi, setAuthToken, checkAuthGate } from '../../api'

const mode = ref('login')
const loading = ref(false)

const tabList = [
  { key: 'login', label: '登录' },
  { key: 'register', label: '创建空间' },
  { key: 'join', label: '加入空间' },
]

const loginEmail = ref('')
const loginPassword = ref('')
const regEmail = ref('')
const regPassword = ref('')
const regName = ref('')
const joinCode = ref('')
const joinEmail = ref('')
const joinPassword = ref('')
const joinName = ref('')

onShow(() => {
  checkAuthGate().then(() => {
    if (uni.getStorageSync('auth_token')) {
      uni.switchTab({ url: '/pages/pick/pick' })
    }
  })
})

async function doLogin() {
  loading.value = true
  try {
    const res = await authApi.login(loginEmail.value.trim(), loginPassword.value)
    if (res.access_token) setAuthToken(res.access_token)
    uni.showToast({ title: '欢迎回来', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/pick/pick' }), 400)
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  loading.value = true
  try {
    const res = await authApi.registerCouple({
      email: regEmail.value.trim(),
      password: regPassword.value,
      display_name: regName.value.trim(),
    })
    if (res.access_token) setAuthToken(res.access_token)
    uni.showModal({
      title: '邀请码（请发给另一半）',
      content: res.join_code || '请在「报表」页退出重新登录查看账号信息',
      showCancel: false,
      success: () => uni.switchTab({ url: '/pages/pick/pick' }),
    })
  } finally {
    loading.value = false
  }
}

async function doJoin() {
  loading.value = true
  try {
    const res = await authApi.joinCouple({
      join_code: joinCode.value.trim(),
      email: joinEmail.value.trim(),
      password: joinPassword.value,
      display_name: joinName.value.trim(),
    })
    if (res.access_token) setAuthToken(res.access_token)
    uni.showToast({ title: '已加入', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/pick/pick' }), 400)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 48rpx 40rpx 80rpx;
  background: linear-gradient(180deg, #fff7ed 0%, #f8f8f7 35%);
}
.hero {
  margin-bottom: 40rpx;
}
.hero-title {
  display: block;
  font-size: 56rpx;
  font-weight: 900;
  color: #1c1917;
  letter-spacing: -1rpx;
}
.hero-sub {
  display: block;
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #78716c;
}
.tabs {
  display: flex;
  gap: 12rpx;
  margin-bottom: 28rpx;
}
.tab {
  flex: 1;
  text-align: center;
  padding: 20rpx 8rpx;
  border-radius: 9999rpx;
  background: #e7e5e4;
}
.tab-on {
  background: linear-gradient(90deg, #9b3f00, #ff7a2c);
}
.tab-t {
  font-size: 26rpx;
  font-weight: 700;
  color: #57534e;
}
.tab-t-on {
  color: #ffffff;
}
.card {
  background: #ffffff;
  border-radius: 40rpx;
  padding: 36rpx 32rpx;
  box-shadow: 0 24rpx 60rpx rgba(124, 45, 18, 0.08);
}
.field {
  margin-bottom: 28rpx;
}
.label {
  display: block;
  font-size: 24rpx;
  font-weight: 600;
  color: #78716c;
  margin-bottom: 10rpx;
}
.input {
  width: 100%;
  height: 88rpx;
  padding: 0 24rpx;
  border-radius: 20rpx;
  background: #f5f5f4;
  font-size: 28rpx;
  color: #1c1917;
  box-sizing: border-box;
}
.btn {
  margin-top: 12rpx;
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 24rpx;
  font-size: 30rpx;
  font-weight: 700;
  border: none;
}
.btn.primary {
  background: linear-gradient(90deg, #9b3f00, #ff7a2c);
  color: #ffffff;
}
.hint {
  display: block;
  margin-top: 24rpx;
  font-size: 22rpx;
  color: #a8a29e;
  line-height: 1.5;
}
</style>

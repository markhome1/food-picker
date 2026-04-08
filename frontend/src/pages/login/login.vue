<template>
  <view class="page">
    <view class="hero">
      <view class="hero-brand">
        <image class="hero-logo" src="/static/logo.svg" mode="aspectFit" />
        <text class="hero-title">food-picker</text>
      </view>
      <text class="hero-sub">情侣或好友组队 · 每组最多 20 人 · 数据仅组内可见</text>
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
        <view class="field space-preset-block">
          <text class="label">空间类型</text>
          <view class="space-preset-row">
            <view
              :class="['space-chip', spacePreset === 'couple' ? 'space-chip-on' : '']"
              @click="spacePreset = 'couple'"
            >
              <text class="space-chip-t">情侣（2 人）</text>
            </view>
            <view
              :class="['space-chip', spacePreset === 'group' ? 'space-chip-on' : '']"
              @click="spacePreset = 'group'"
            >
              <text class="space-chip-t">好友组队</text>
            </view>
          </view>
          <picker
            v-if="spacePreset === 'group'"
            mode="selector"
            :range="groupSizeLabels"
            :value="groupSizeIndex"
            @change="onGroupSizeChange"
          >
            <view class="picker-row">
              <text class="label-inline">人数上限</text>
              <text class="picker-value">{{ groupSizeLabels[groupSizeIndex] }}</text>
              <text class="picker-chev">›</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="label">邮箱</text>
          <input class="input" v-model="regEmail" type="text" placeholder="创建者邮箱" />
        </view>
        <view class="field">
          <text class="label">邮箱验证码</text>
          <view class="otp-row">
            <input
              class="input otp-input"
              v-model="regOtp"
              type="text"
              maxlength="6"
              placeholder="6 位数字"
            />
            <button
              class="btn-ghost"
              :disabled="regCooldown > 0 || loading"
              @click="sendRegCode"
            >
              {{ regCooldown > 0 ? regCooldown + 's' : '获取验证码' }}
            </button>
          </view>
        </view>
        <view class="field">
          <text class="label">密码</text>
          <input class="input" v-model="regPassword" password placeholder="至少 6 位" />
        </view>
        <view class="field">
          <text class="label">昵称（可选）</text>
          <input class="input" v-model="regName" type="text" placeholder="怎么称呼你" />
        </view>
        <button class="btn primary" :loading="loading" @click="doRegister">创建空间</button>
        <text v-if="emailOtpHint" class="hint hint-warn">{{ emailOtpHint }}</text>
        <text class="hint">请先获取邮箱验证码；创建成功后会得到邀请码，发给伙伴加入（每组最多 20 人）。</text>
      </template>

      <template v-else>
        <view class="field">
          <text class="label">邀请码</text>
          <input class="input" v-model="joinCode" type="text" placeholder="例如 ABC123-DEF456" />
        </view>
        <view class="field">
          <text class="label">邮箱</text>
          <input class="input" v-model="joinEmail" type="text" placeholder="使用未注册过的邮箱" />
        </view>
        <view class="field">
          <text class="label">邮箱验证码</text>
          <view class="otp-row">
            <input
              class="input otp-input"
              v-model="joinOtp"
              type="text"
              maxlength="6"
              placeholder="6 位数字"
            />
            <button
              class="btn-ghost"
              :disabled="joinCooldown > 0 || loading"
              @click="sendJoinCode"
            >
              {{ joinCooldown > 0 ? joinCooldown + 's' : '获取验证码' }}
            </button>
          </view>
        </view>
        <view class="field">
          <text class="label">密码</text>
          <input class="input" v-model="joinPassword" password placeholder="至少 6 位" />
        </view>
        <view class="field">
          <text class="label">昵称（可选）</text>
          <input class="input" v-model="joinName" type="text" placeholder="怎么称呼你" />
        </view>
        <button class="btn primary" :loading="loading" @click="doJoin">加入空间</button>
        <text v-if="emailOtpHint" class="hint hint-warn">{{ emailOtpHint }}</text>
        <text class="hint">人数达到创建者设定上限后无法再加入；加入前需验证邮箱。</text>
      </template>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { authApi, setAuthToken, request } from '../../api'

const mode = ref('login')
const loading = ref(false)
const emailOtpHint = ref('')

const regOtp = ref('')
const joinOtp = ref('')
const regCooldown = ref(0)
const joinCooldown = ref(0)
let regTimer = null
let joinTimer = null

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

/** 情侣 2 人；好友组队可选 3～20 人 */
const spacePreset = ref('couple')
const groupSizeIndex = ref(0)
const groupSizeLabels = Array.from({ length: 18 }, (_, i) => `${i + 3} 人`)

function onGroupSizeChange(e) {
  const v = e.detail && e.detail.value
  groupSizeIndex.value = typeof v === 'number' ? v : parseInt(String(v), 10) || 0
}

function registerMaxMembers() {
  if (spacePreset.value === 'couple') return 2
  return groupSizeIndex.value + 3
}

// 勿在此调用 checkAuthGate：无 token 时会 reLaunch 本页，H5 上 onShow 易在输入时重复触发导致整页重载、输入被清空。
onShow(() => {
  const token = uni.getStorageSync('auth_token')
  if (!token) return
  request({ url: '/api/auth/me', method: 'GET', silent: true })
    .then(() => uni.switchTab({ url: '/pages/pick/pick' }))
    .catch(() => {})
})

onMounted(async () => {
  try {
    const st = await authApi.status()
    const ch = st.email_otp && st.email_otp.channel
    if (ch === 'dev_log') {
      emailOtpHint.value = '本地调试：验证码会打印在后端终端日志（未配置 RESEND 时）。'
    } else if (ch === 'none') {
      emailOtpHint.value = '服务器未配置发信（RESEND_API_KEY），无法发送验证码。'
    } else {
      emailOtpHint.value = ''
    }
  } catch {
    emailOtpHint.value = ''
  }
})

onUnmounted(() => {
  if (regTimer) clearInterval(regTimer)
  if (joinTimer) clearInterval(joinTimer)
})

function startCooldown(which) {
  if (which === 'reg') {
    regCooldown.value = 60
    if (regTimer) clearInterval(regTimer)
    regTimer = setInterval(() => {
      regCooldown.value--
      if (regCooldown.value <= 0 && regTimer) {
        clearInterval(regTimer)
        regTimer = null
      }
    }, 1000)
  } else {
    joinCooldown.value = 60
    if (joinTimer) clearInterval(joinTimer)
    joinTimer = setInterval(() => {
      joinCooldown.value--
      if (joinCooldown.value <= 0 && joinTimer) {
        clearInterval(joinTimer)
        joinTimer = null
      }
    }, 1000)
  }
}

async function sendRegCode() {
  const email = regEmail.value.trim()
  if (!email) {
    uni.showToast({ title: '请先填写邮箱', icon: 'none' })
    return
  }
  loading.value = true
  try {
    await authApi.sendEmailCode(email, 'register_couple')
    uni.showToast({ title: '已发送，请查收邮件', icon: 'none' })
    startCooldown('reg')
  } finally {
    loading.value = false
  }
}

async function sendJoinCode() {
  const email = joinEmail.value.trim()
  if (!email) {
    uni.showToast({ title: '请先填写邮箱', icon: 'none' })
    return
  }
  loading.value = true
  try {
    await authApi.sendEmailCode(email, 'join_couple')
    uni.showToast({ title: '已发送，请查收邮件', icon: 'none' })
    startCooldown('join')
  } finally {
    loading.value = false
  }
}

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
      verification_code: regOtp.value.trim(),
      max_members: registerMaxMembers(),
    })
    if (res.access_token) setAuthToken(res.access_token)
    uni.showModal({
      title: '邀请码（发给伙伴）',
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
      verification_code: joinOtp.value.trim(),
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
.hero-brand {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16rpx;
}
.hero-logo {
  width: 80rpx;
  height: 80rpx;
  flex-shrink: 0;
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
.space-preset-block {
  margin-bottom: 28rpx;
}
.space-preset-row {
  display: flex;
  flex-direction: row;
  gap: 16rpx;
  margin-top: 10rpx;
}
.space-chip {
  flex: 1;
  text-align: center;
  padding: 20rpx 12rpx;
  border-radius: 20rpx;
  background: #f5f5f4;
  border: 2rpx solid transparent;
}
.space-chip-on {
  background: #fff7ed;
  border-color: rgba(155, 63, 0, 0.45);
}
.space-chip-t {
  font-size: 26rpx;
  font-weight: 700;
  color: #57534e;
}
.space-chip-on .space-chip-t {
  color: #9b3f00;
}
.picker-row {
  margin-top: 16rpx;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 20rpx 24rpx;
  background: #f5f5f4;
  border-radius: 20rpx;
}
.label-inline {
  font-size: 26rpx;
  font-weight: 600;
  color: #78716c;
  flex: 1;
}
.picker-value {
  font-size: 28rpx;
  font-weight: 700;
  color: #1c1917;
  margin-right: 8rpx;
}
.picker-chev {
  font-size: 32rpx;
  color: #a8a29e;
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
.hint-warn {
  color: #b45309;
}
.otp-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16rpx;
}
.otp-input {
  flex: 1;
  min-width: 0;
}
.btn-ghost {
  flex-shrink: 0;
  height: 88rpx;
  line-height: 88rpx;
  padding: 0 24rpx;
  font-size: 26rpx;
  font-weight: 700;
  color: #9b3f00;
  background: #fff7ed;
  border: 2rpx solid rgba(155, 63, 0, 0.35);
  border-radius: 20rpx;
}
.btn-ghost[disabled] {
  opacity: 0.45;
  color: #78716c;
}
</style>

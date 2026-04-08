function resolveApiBase() {
  const fromEnv = import.meta.env.VITE_API_BASE
  if (typeof fromEnv === 'string' && fromEnv.length) return fromEnv.replace(/\/$/, '')
  if (typeof window === 'undefined') return ''
  const port = String(window.location.port || '')
  // 本地 Vite/uni 开发服常见端口：一律走相对路径 /api，由 vite 代理到后端（避免预览环境 DEV 标识异常仍去打 127.0.0.1 导致 404）
  if (port === '5177' || port === '5173' || port === '5174' || port === '8080') {
    return ''
  }
  const dev = import.meta.env.DEV
  const plat = import.meta.env.UNI_PLATFORM
  const isH5Like = plat === 'h5' || plat === 'web'
  if (dev && isH5Like) {
    return ''
  }
  return ''
}

export const BASE_URL = resolveApiBase()

export function getAuthHeaders() {
  const token = uni.getStorageSync('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function setAuthToken(token) {
  if (token) uni.setStorageSync('auth_token', token)
  else uni.removeStorageSync('auth_token')
}

export function clearAuthToken() {
  uni.removeStorageSync('auth_token')
}

/** 已在登录页时返回 true，避免 checkAuthGate 再 reLaunch 导致整页重载、输入框被清空（H5 onShow 会多次触发） */
export function isCurrentPageLogin() {
  try {
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1]
    const route = cur && cur.route ? String(cur.route) : ''
    return route.includes('login/login')
  } catch {
    return false
  }
}

export const request = (options) => {
  const silent = options.silent === true
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...options.header
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          if (!silent) {
            const d = res.data
            const msg =
              (typeof d?.detail === 'string' && d.detail) ||
              (Array.isArray(d?.detail) && d.detail[0]?.msg) ||
              (d?.message && String(d.message)) ||
              `请求失败(${res.statusCode})`
            uni.showToast({ title: msg, icon: 'none' })
          }
          reject(res.data)
        }
      },
      fail: (err) => {
        if (!silent) {
          uni.showToast({ title: '网络错误', icon: 'none' })
        }
        reject(err)
      }
    })
  })
}

// 餐厅 API
export const restaurantApi = {
  list: (params) => request({ url: '/api/restaurants', data: params }),
  get: (id) => request({ url: `/api/restaurants/${id}` }),
  create: (data) => request({ url: '/api/restaurants', method: 'POST', data }),
  batch: (items) =>
    request({ url: '/api/restaurants/batch', method: 'POST', data: { items } }),
  update: (id, data, opts = {}) =>
    request({ url: `/api/restaurants/${id}`, method: 'PATCH', data, silent: opts.silent === true }),
  remove: (id) => request({ url: `/api/restaurants/${id}`, method: 'DELETE' }),
  random: (params) => request({ url: '/api/restaurants/random', data: params }),
}

// 就餐记录 API
export const recordApi = {
  list: (params) => request({ url: '/api/records', data: params }),
  create: (data) => request({ url: '/api/records', method: 'POST', data }),
  remove: (id) => request({ url: `/api/records/${id}`, method: 'DELETE' }),
  stats: (params) => request({ url: '/api/records/stats', data: params }),
}

// 抖音链接 / 截图 OCR 导入
export const importApi = {
  douyin: (url) =>
    request({ url: '/api/import/douyin', method: 'POST', data: { url } }),
  addByName: (name, source_url = '') =>
    request({
      url: '/api/import/add-by-name',
      method: 'POST',
      data: { name, source_url, boards: 'my_pick' },
    }),
}

export function importOcrUpload(filePath) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${BASE_URL}/api/import/ocr-candidates`,
      filePath,
      name: 'file',
      header: {
        ...getAuthHeaders(),
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(res.data))
          } catch (e) {
            reject(e)
          }
        } else {
          try {
            const j = JSON.parse(res.data)
            uni.showToast({ title: (j.detail && String(j.detail)) || 'OCR 失败', icon: 'none', duration: 3500 })
          } catch (_) {
            uni.showToast({ title: 'OCR 失败', icon: 'none' })
          }
          reject(res)
        }
      },
      fail: (err) => {
        uni.showToast({ title: '上传失败', icon: 'none' })
        reject(err)
      },
    })
  })
}

// 登录 / 共享空间（按 couple_account_id 隔离数据）
export const authApi = {
  status: () => request({ url: '/api/auth/status', method: 'GET', silent: true }),
  me: () => request({ url: '/api/auth/me', method: 'GET' }),
  login: (email, password) =>
    request({ url: '/api/auth/login', method: 'POST', data: { email, password } }),
  sendEmailCode: (email, purpose, extra = {}) =>
    request({
      url: '/api/auth/send-email-code',
      method: 'POST',
      data: { email, purpose, ...extra },
    }),
  registerCouple: (data) =>
    request({ url: '/api/auth/register-couple', method: 'POST', data }),
  joinCouple: (data) =>
    request({ url: '/api/auth/join-couple', method: 'POST', data }),
  /** @returns {Promise<object>} 多空间时 reject 的 payload 含 detail.error === 'pick_space' */
  login: (email, password, coupleAccountId) =>
    new Promise((resolve, reject) => {
      uni.request({
        url: `${BASE_URL}/api/auth/login`,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: {
          email,
          password,
          ...(coupleAccountId != null ? { couple_account_id: coupleAccountId } : {}),
        },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
          else reject(res.data || {})
        },
        fail: (err) => reject(err),
      })
    }),
}

/**
 * 若后端要求登录：无/无效 token 时跳转登录页（已在登录页则不再 reLaunch）。
 * @returns {Promise<boolean>} 是否允许继续加载当前页业务数据（false 时已发起 reLaunch 或应停止请求，避免 401 刷屏）
 */
export async function checkAuthGate() {
  let st
  try {
    st = await request({ url: '/api/auth/status', method: 'GET', silent: true })
  } catch {
    return true
  }
  if (!st || !st.auth_required) return true
  const token = uni.getStorageSync('auth_token')
  if (!token) {
    if (!isCurrentPageLogin()) {
      uni.reLaunch({ url: '/pages/login/login' })
    }
    return false
  }
  try {
    await request({ url: '/api/auth/me', method: 'GET', silent: true })
    return true
  } catch {
    clearAuthToken()
    if (!isCurrentPageLogin()) {
      uni.reLaunch({ url: '/pages/login/login' })
    }
    return false
  }
}

// 高德 API（地理编码用 query，避免部分端 GET + data 对中文参数处理异常）
export const amapApi = {
  geocode: (address) =>
    request({
      url: `/api/amap/geocode?address=${encodeURIComponent(address)}`,
      method: 'GET',
    }),
  poi: (keyword, page) => request({ url: '/api/amap/poi', data: { keyword, page } }),
  poiAround: (longitude, latitude, radius = 3000, page = 1) =>
    request({
      url: `/api/amap/poi-around?longitude=${longitude}&latitude=${latitude}&radius=${radius}&page=${page}`,
      method: 'GET',
    }),
  /** 点击地图某点，逆地理+周边 POI，用于点选图面上的店铺 */
  regeoPois: (longitude, latitude, radius = 120) =>
    request({
      url: `/api/amap/regeo-pois?longitude=${longitude}&latitude=${latitude}&radius=${radius}`,
      method: 'GET',
      silent: true,
    }),
  enrichPoi: (name, longitude, latitude) =>
    request({
      url: `/api/amap/enrich-poi?name=${encodeURIComponent(name)}&longitude=${longitude}&latitude=${latitude}`,
      method: 'GET',
      silent: true,
    }),
}

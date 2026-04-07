/** H5 高德 JS API：读 manifest 编译进 __uniConfig 的 key / 安全密钥 */

export function getAmapCredentials() {
  // eslint-disable-next-line no-undef
  const cfg = typeof __uniConfig !== 'undefined' ? __uniConfig : {}
  return {
    key: cfg.aMapKey || '',
    securityJsCode: cfg.aMapSecurityJsCode || '',
  }
}

export function loadAmapScript(key, securityJsCode) {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'))
  window._AMapSecurityConfig = { securityJsCode }
  return new Promise((resolve, reject) => {
    if (window.AMap) {
      resolve()
      return
    }
    const s = document.createElement('script')
    s.async = true
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('amap script'))
    document.head.appendChild(s)
  })
}

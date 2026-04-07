<script>
export default {
  onLaunch: function () {
    console.log('App Launch')
  },
  onShow: function () {
    console.log('App Show')
  },
  onHide: function () {
    console.log('App Hide')
  },
}
</script>

<style>
/* 全局设计变量 — Figma Premium Restaurant */
page {
  /* Primary: deep brown-orange from Figma #9b3f00 */
  --color-primary: #9b3f00;
  --color-primary-light: #ff7a2c;
  --color-primary-dark: #7c2d12;
  --color-primary-bg: rgba(155, 63, 0, 0.06);
  --color-primary-gradient: linear-gradient(to right, #9b3f00, #ff7a2c);
  /* Neutral palette from Figma */
  --color-bg: #f8f8f7;
  --color-bg-card: #ffffff;
  --color-bg-elevated: #f5f5f4;
  --color-bg-muted: #e8e8e7;
  --color-text: #2e2f2f;
  --color-text-secondary: #5b5c5b;
  --color-text-muted: #767776;
  --color-border: rgba(173, 173, 172, 0.15);
  --color-border-light: rgba(173, 173, 172, 0.1);
  /* Accent badges from Figma */
  --color-accent-orange-bg: #ffedd5;
  --color-accent-orange-text: #9a3412;
  --color-accent-blue-bg: #dbeafe;
  --color-accent-blue-text: #1e40af;
  --color-review-bg: rgba(255, 195, 189, 0.2);
  --color-review-border: rgba(255, 195, 189, 0.3);
  /* Semantic */
  --color-success: #16a34a;
  --color-danger: #dc2626;
  --color-red-dot: #ef4444;
  --color-blue-dot: #3b82f6;
  /* Radius from Figma — large rounded cards */
  --radius-sm: 16rpx;
  --radius-md: 24rpx;
  --radius-lg: 48rpx;
  --radius-xl: 64rpx;
  --radius-full: 9999rpx;
  /* Shadows from Figma — warm undertones */
  --shadow-xs: 0 2rpx 4rpx rgba(124, 45, 18, 0.04);
  --shadow-sm: 0 4rpx 12rpx rgba(124, 45, 18, 0.05);
  --shadow-md: 0 8rpx 24rpx rgba(124, 45, 18, 0.06);
  --shadow-lg: 0 24rpx 48rpx rgba(124, 45, 18, 0.08);
  --shadow-card: 0 50rpx 100rpx -24rpx rgba(124, 45, 18, 0.05);
  --shadow-pill: 0 40rpx 50rpx -10rpx rgba(0, 0, 0, 0.1), 0 16rpx 20rpx -12rpx rgba(0, 0, 0, 0.1);
  --shadow-btn: 0 20rpx 30rpx -6rpx rgba(155, 63, 0, 0.2), 0 8rpx 12rpx -8rpx rgba(155, 63, 0, 0.2);
  background-color: var(--color-bg);
  font-family: 'PingFang SC', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 全局基础样式 */
view, text {
  box-sizing: border-box;
}
</style>

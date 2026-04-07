<template>
  <view class="container">
    <view class="form">
      <view class="form-item">
        <text class="label">餐厅名称 *</text>
        <input class="input" v-model="form.name" placeholder="请输入餐厅名称" />
      </view>
      <view class="form-item">
        <text class="label">地址</text>
        <input class="input" v-model="form.address" placeholder="请输入地址" />
      </view>
      <view class="form-item">
        <text class="label">人均价格（元）</text>
        <input class="input" type="digit" v-model="form.avg_price" placeholder="如 50" />
      </view>
      <view class="form-item">
        <text class="label">价格档位</text>
        <picker :range="tierLabels" :value="tierIndex" @change="onTierChange">
          <view class="picker-value">{{ form.price_tier || '请选择' }}</view>
        </picker>
      </view>
      <view class="form-item">
        <text class="label">分类</text>
        <input class="input" v-model="form.category" placeholder="如: 火锅、川菜、烧烤" />
      </view>
      <view class="form-item">
        <text class="label">标签（逗号分隔）</text>
        <input class="input" v-model="form.tags" placeholder="如: 网红,辣,推荐" />
      </view>
      <view class="form-item">
        <text class="label">来源</text>
        <picker :range="sourceLabels" :value="sourceIndex" @change="onSourceChange">
          <view class="picker-value">{{ form.source || '请选择' }}</view>
        </picker>
      </view>
      <view class="form-item">
        <text class="label">高德地图 POI 评分（五星）</text>
        <input class="input" type="digit" v-model="form.rating" placeholder="从高德商户页核对，如 4.5" />
      </view>
      <view class="form-item">
        <text class="label">大众点评评分（五星）</text>
        <input class="input" type="digit" v-model="form.dianping_rating" placeholder="从点评店铺页核对，如 4.8" />
      </view>
      <view class="form-item">
        <text class="label">大众点评店铺链接</text>
        <input class="input" v-model="form.dianping_url" placeholder="https:// 店铺页 URL，便于用户跳转核对" />
      </view>
      <view class="form-item">
        <text class="label">点评原文摘录（可选）</text>
        <input class="input" v-model="form.dianping_snippet" placeholder="从点评页复制一句真实评价，勿编造" />
      </view>
      <view class="form-item">
        <text class="label">其它权威来源名称</text>
        <input class="input" v-model="form.authority_label" placeholder="如：黑珍珠、高德指南、米其林指南" />
      </view>
      <view class="form-item">
        <text class="label">该来源评分或档位说明</text>
        <input class="input" type="digit" v-model="form.authority_rating" placeholder="若可量化为五星可填数字，否则可留空" />
      </view>
      <view class="form-item">
        <text class="label">权威来源官方链接</text>
        <input class="input" v-model="form.authority_url" placeholder="榜单或介绍页 URL" />
      </view>
      <view class="form-item">
        <text class="label">封面图 URL</text>
        <input class="input" v-model="form.image_url" placeholder="https:// 餐厅头图" />
      </view>
      <view class="form-item">
        <text class="label">来源链接（抖音笔记 / 视频）</text>
        <input class="input" v-model="form.source_url" placeholder="粘贴抖音分享链接" />
      </view>
      <view class="form-item">
        <text class="label">榜单归属</text>
        <view class="board-row" @click="form.board_my_pick = !form.board_my_pick">
          <text class="board-label">自己精选（常吃店）</text>
          <text class="board-flag">{{ form.board_my_pick ? '✓' : '○' }}</text>
        </view>
        <view class="board-row" @click="form.board_viral = !form.board_viral">
          <text class="board-label">网红打卡（博主推荐）</text>
          <text class="board-flag">{{ form.board_viral ? '✓' : '○' }}</text>
        </view>
      </view>

      <view class="btn-save" @click="save">{{ isEdit ? '保存修改' : '添加餐厅' }}</view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { restaurantApi } from '../../api'

const isEdit = ref(false)
const editId = ref(null)

const tierLabels = ['0-10', '10-20', '20-50', '50-100', '100+']
const tierIndex = ref(2)
const sourceLabels = ['manual', 'douyin', 'amap', 'dianping']
const sourceIndex = ref(0)

const form = ref({
  name: '',
  address: '',
  avg_price: '',
  price_tier: '20-50',
  category: '',
  tags: '',
  source: 'manual',
  rating: '',
  dianping_rating: '',
  dianping_url: '',
  dianping_snippet: '',
  authority_label: '',
  authority_rating: '',
  authority_url: '',
  image_url: '',
  source_url: '',
  board_my_pick: false,
  board_viral: false,
})

const boardsToStr = () => {
  const p = []
  if (form.value.board_my_pick) p.push('my_pick')
  if (form.value.board_viral) p.push('viral')
  return p.join(';')
}

const strToBoards = (s) => {
  const set = new Set((s || '').split(';').map((x) => x.trim()).filter(Boolean))
  return {
    board_my_pick: set.has('my_pick'),
    board_viral: set.has('viral'),
  }
}

const onTierChange = (e) => {
  tierIndex.value = e.detail.value
  form.value.price_tier = tierLabels[e.detail.value]
}
const onSourceChange = (e) => {
  sourceIndex.value = e.detail.value
  form.value.source = sourceLabels[e.detail.value]
}

const save = async () => {
  if (!form.value.name) {
    uni.showToast({ title: '请输入餐厅名称', icon: 'none' })
    return
  }
  const data = { ...form.value }
  delete data.board_my_pick
  delete data.board_viral
  data.boards = boardsToStr()
  if (data.avg_price) data.avg_price = parseFloat(data.avg_price)
  else delete data.avg_price
  if (data.rating) data.rating = parseFloat(data.rating)
  else delete data.rating
  data.dianping_url = String(data.dianping_url || '').trim()
  data.dianping_snippet = String(data.dianping_snippet || '').trim()
  data.authority_label = String(data.authority_label || '').trim()
  data.authority_url = String(data.authority_url || '').trim()
  if (data.dianping_rating) data.dianping_rating = parseFloat(data.dianping_rating)
  else data.dianping_rating = null
  if (data.authority_rating) data.authority_rating = parseFloat(data.authority_rating)
  else data.authority_rating = null

  try {
    if (isEdit.value) {
      await restaurantApi.update(editId.value, data)
      uni.showToast({ title: '已更新' })
    } else {
      await restaurantApi.create(data)
      uni.showToast({ title: '已添加' })
    }
    setTimeout(() => uni.navigateBack(), 500)
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  const options = currentPage.$page ? currentPage.$page.options : currentPage.options
  if (options && options.id) {
    isEdit.value = true
    editId.value = parseInt(options.id)
    loadRestaurant(editId.value)
  }
})

const loadRestaurant = async (id) => {
  const r = await restaurantApi.get(id)
  form.value.name = r.name
  form.value.address = r.address
  form.value.avg_price = r.avg_price ? String(r.avg_price) : ''
  form.value.price_tier = r.price_tier
  form.value.category = r.category
  form.value.tags = r.tags
  form.value.source = r.source
  form.value.rating = r.rating != null ? String(r.rating) : ''
  form.value.dianping_rating = r.dianping_rating != null ? String(r.dianping_rating) : ''
  form.value.dianping_url = r.dianping_url || ''
  form.value.dianping_snippet = r.dianping_snippet || ''
  form.value.authority_label = r.authority_label || ''
  form.value.authority_rating = r.authority_rating != null ? String(r.authority_rating) : ''
  form.value.authority_url = r.authority_url || ''
  form.value.image_url = r.image_url || ''
  form.value.source_url = r.source_url || ''
  const b = strToBoards(r.boards || '')
  form.value.board_my_pick = b.board_my_pick
  form.value.board_viral = b.board_viral
  tierIndex.value = tierLabels.indexOf(r.price_tier)
  sourceIndex.value = sourceLabels.indexOf(r.source)
}
</script>

<style scoped>
.container {
  padding: 32rpx 24rpx;
  min-height: 100vh;
  background: var(--color-bg);
}
.form {
  background: var(--color-bg-card); border-radius: var(--radius-xl);
  padding: 36rpx 32rpx; box-shadow: var(--shadow-card);
  border: 1rpx solid var(--color-border-light);
}
.form-item { margin-bottom: 28rpx; }
.label {
  font-size: 24rpx; color: var(--color-text-muted); margin-bottom: 12rpx;
  display: block; font-weight: 600; letter-spacing: 2rpx;
}
.input {
  border: 1rpx solid var(--color-border); border-radius: var(--radius-lg);
  padding: 22rpx 24rpx; font-size: 28rpx; color: var(--color-text);
  background: var(--color-bg-elevated);
}
.picker-value {
  border: 1rpx solid var(--color-border); border-radius: var(--radius-lg);
  padding: 22rpx 24rpx; font-size: 28rpx; color: var(--color-text);
  background: var(--color-bg-elevated);
}
.btn-save {
  background: var(--color-primary-gradient); color: #fff;
  padding: 26rpx; border-radius: var(--radius-full);
  text-align: center; font-size: 30rpx; font-weight: 700;
  margin-top: 16rpx;
  box-shadow: var(--shadow-btn);
}
.btn-save:active { opacity: 0.9; }

.board-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  padding: 22rpx 24rpx;
  margin-bottom: 12rpx;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-lg);
  border: 1rpx solid var(--color-border);
}
.board-label {
  font-size: 28rpx;
  color: var(--color-text);
}
.board-flag {
  font-size: 32rpx;
  color: #9b3f00;
  font-weight: 700;
}
</style>

# 环境配置 - 今天吃啥

## 必需工具
- Python 3.9+
- Node.js 18+
- pnpm 10+

## 本地运行
### 后端
```bash
cd E:\food-picker\backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000 --app-dir E:\food-picker\backend
```
API 文档: http://127.0.0.1:8000/docs

### 前端
```bash
cd E:\food-picker\frontend
pnpm install
pnpm dev:h5
```
访问: http://localhost:5173/

## 环境变量
后端 `.env` 文件:
```
AMAP_KEY=your_amap_key_here
DATABASE_URL=sqlite:///data/food_picker.db
```

## 已知问题
- Python 3.9 不支持 `X | None` 语法，使用 `Optional[X]`
- 后台终端需用 `--app-dir` 参数或 `pnpm --dir` 指定目录
- 高德 API Key 需到 https://lbs.amap.com/ 申请

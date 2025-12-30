# OutfitMatch 快速開始指南

本指南將幫助你在 15 分鐘內啟動 OutfitMatch 專案。

## 前置需求

- Python 3.8+
- Node.js 16+
- Neo4j 5.0+（需要支援向量索引）
- OpenAI API Key
- Instagram 帳號（用於抓取穿搭貼文）

## 步驟 1：設置 Neo4j

### 選項 A：使用 Neo4j Desktop（推薦）
1. 下載並安裝 [Neo4j Desktop](https://neo4j.com/download/)
2. 創建新的資料庫專案
3. 設置密碼（記住這個密碼）
4. 啟動資料庫

### 選項 B：使用 Docker
```bash
docker run \
    --name neo4j-outfitmatch \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    neo4j:latest
```

## 步驟 2：配置環境變數

```bash
cd OutfitMatch
cp .env.example .env
```

編輯 `.env` 檔案：
```env
# 必填項目
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
NEO4J_PASSWORD=your_neo4j_password
OPENAI_API_KEY=sk-your-openai-key

# 預設值（通常不需要改）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
SERVER_PORT=8000
```

## 步驟 3：安裝後端依賴

```bash
# 創建虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

## 步驟 4：初始化資料庫

```bash
# 創建 Neo4j schema、索引和基礎資料
python database/init_neo4j_schema.py
```

你應該看到：
```
✅ Created constraint: (u:User)
✅ Created index: (p:Product)
✅ Created vector index: post_image_index
✅ Initialized 16 style nodes
✅ Initialized 5 category nodes
```

## 步驟 5：載入商品資料

```bash
# 快速測試：只載入前 50 筆
python loader/shop_neo4j.py --nrows 50

# 完整載入（需要較長時間，因為要用 LLM 預測風格）
python loader/shop_neo4j.py
```

預期輸出：
```
📄 Reading original CSV and predicting styles
🔮 Predicting styles for 50 products...
💾 Style prediction completed
🚀 Starting import of 50 products to Neo4j...
Progress: 50/50 products imported (100.0%)
✅ Import completed: 50 products imported, 0 skipped
📊 Total products in database: 50
```

## 步驟 6：載入 Instagram 穿搭資料（可選）

```bash
# 抓取 20 篇穿搭貼文
python loader/instagram_neo4j.py --max_posts 20
```

⚠️ **注意**：Instagram 可能會限制爬蟲，建議：
- 第一次只抓少量貼文（10-20 篇）
- 不要頻繁執行
- 如果被限制，可以跳過這步先測試商品推薦功能

## 步驟 7：建立推薦關係

```bash
# 自動分析並建立商品搭配關係
python database/build_relationships.py
```

預期輸出：
```
✅ Created 145 GOES_WITH relationships
✅ Created 78 top-bottom outfit relationships
✅ Created 234 INSPIRED_BY relationships
```

## 步驟 8：啟動後端服務

```bash
# 在 OutfitMatch 目錄下
python server.py
```

看到以下訊息表示成功：
```
=== Starting Flask development server ===
Debug mode: ON
Host: 0.0.0.0
Port: 8000
* Running on http://0.0.0.0:8000
```

## 步驟 9：啟動前端

開啟新的終端視窗：

```bash
cd ui
npm install
npm run dev
```

看到：
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

## 步驟 10：測試系統

1. 在瀏覽器打開 `http://localhost:5173`
2. 上傳一張穿搭圖片（可以用 `OutfitMatch/test/images/` 中的圖片）
3. 輸入查詢條件，例如：「2000元以下的上衣」
4. 查看推薦結果！

## 驗證安裝

### 檢查後端 API
```bash
curl http://localhost:8000/api/health
```

應該返回：
```json
{
  "status": "healthy",
  "timestamp": "2025-12-30T..."
}
```

### 檢查 Neo4j 資料
在 Neo4j Browser (http://localhost:7474) 執行：

```cypher
// 查看節點統計
MATCH (n) RETURN labels(n)[0] as type, count(n) as count

// 查看關係統計
MATCH ()-[r]->() RETURN type(r) as type, count(r) as count

// 查看範例商品
MATCH (p:Product)-[:HAS_STYLE]->(s:Style)
MATCH (p)-[:OF_BRAND]->(b:Brand)
RETURN p.name, p.price, b.name, collect(s.name) LIMIT 5
```

## 常見問題排除

### 問題 1：Neo4j 連線失敗
```
ConnectionError: Unable to connect to Neo4j
```

**解決方案**：
1. 確認 Neo4j 服務已啟動
2. 檢查 `.env` 中的 `NEO4J_URI` 和 `NEO4J_PASSWORD`
3. 在 Neo4j Browser 測試連線

### 問題 2：沒有商品資料
```
找不到符合條件的商品
```

**解決方案**：
1. 確認已執行 `python loader/shop_neo4j.py`
2. 在 Neo4j Browser 執行：`MATCH (p:Product) RETURN count(p)`
3. 如果數量為 0，重新載入商品資料

### 問題 3：向量索引錯誤
```
Unable to get index provider for label
```

**解決方案**：
- 確保使用 Neo4j 5.0+ 版本
- 向量索引需要企業版或 AuraDB（或使用 [Neo4j Vector Plugin](https://neo4j.com/docs/vector/))

### 問題 4：OpenAI API 錯誤
```
RateLimitError: You exceeded your current quota
```

**解決方案**：
1. 檢查 OpenAI 帳戶額度
2. 在 `.env` 設置 `STYLE_PREDICTION_MODEL=gpt-4o-mini`（更便宜）
3. 使用 `--skip_prediction` 跳過風格預測

### 問題 5：前後端連線失敗
```
Failed to fetch
```

**解決方案**：
1. 確認後端在 Port 8000 運行
2. 檢查 `ui/src/config/chat.ts` 中的 `BASE_URL`
3. 確認 CORS 設定正確

## 下一步

- 📖 閱讀 [ARCHITECTURE.md](../ARCHITECTURE.md) 了解系統架構
- 🔧 調整 `.env` 中的 LLM 模型降低成本
- 📊 在 Neo4j Browser 探索圖資料結構
- 🚀 加入更多商品資料
- 🎨 自定義風格標籤

## 需要幫助？

- 查看專案 Issues
- 閱讀完整文檔
- 檢查 Neo4j 和 OpenAI 官方文檔

祝使用愉快！🎉

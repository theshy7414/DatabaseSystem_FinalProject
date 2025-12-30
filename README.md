# OutfitMatch 🎨👗

**基於 Neo4j 圖資料庫的智能穿搭推薦系統**

結合 Instagram 穿搭分析、圖神經網路關係推薦、圖片相似度搜尋，打造個性化穿搭建議。

## 專案特色

- 🎯 **圖關係推薦**：利用 Neo4j 圖資料庫建立商品-風格-穿搭的多維關係
- 🖼️ **圖片智能分析**：自動分割服飾區域、生成視覺 embedding
- 🤖 **AI 風格預測**：使用 GPT-4o 自動標註穿搭風格
- 🔍 **混合搜尋**：結合向量相似度 + 圖關係的智能推薦
- 📱 **現代化介面**：React + TypeScript 前端，即時互動體驗

## 架構設計

詳見 [ARCHITECTURE.md](ARCHITECTURE.md) 了解完整的圖資料庫設計。

### 核心技術棧

**後端**：
- Neo4j（圖資料庫 + 向量索引）
- Flask（API 服務器）
- OpenAI GPT-4o（自然語言處理）
- DINOv2（圖片 embedding）
- Segformer（服飾分割）

**前端**：
- React + TypeScript
- Vite
- Tailwind CSS

## 快速開始

### 1. 環境設置

```bash
# 複製環境變數範本
cd OutfitMatch
cp .env.example .env

# 編輯 .env 填入你的憑證
# 必填：OPENAI_API_KEY, NEO4J_PASSWORD, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
```

`.env` 檔案範例：
```env
# Instagram（用於抓取穿搭貼文）
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Neo4j（確保已啟動 Neo4j 服務）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI
OPENAI_API_KEY=sk-your-key

# Server
SERVER_PORT=8000
```

### 2. 安裝依賴

```bash
# 後端
cd OutfitMatch
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

# 前端
cd ..\ui
npm install
```

### 3. 初始化資料庫

```bash
# 回到 OutfitMatch 目錄
cd ..\OutfitMatch

# 初始化 Neo4j schema（創建索引、約束、基礎資料）
python database/init_neo4j_schema.py
```

### 4. 載入資料

```bash
# 載入商品資料（從 CSV 到 Neo4j）
python loader/shop_neo4j.py --products_csv data/queenshop_all_products.csv

# 參數說明：
# --nrows 100               # 只處理前 100 筆（測試用）
# --skip_prediction         # 跳過 LLM 風格預測（使用已處理的 CSV）

# 抓取 Instagram 穿搭貼文
python loader/instagram_neo4j.py --max_posts 50

# 參數說明：
# --max_posts 50            # 抓取 50 篇貼文（預設值）
```

### 5. 啟動服務

```bash
# 啟動後端 API 服務器（Port 8000）
python server.py

# 新開一個終端，啟動前端
cd ..\ui
npm run dev
# 打開瀏覽器訪問 http://localhost:5173
```

## 使用方式

1. **上傳穿搭圖片**：系統會自動分析風格
2. **輸入需求**：例如「2000元以下的韓系上衣」
3. **獲得推薦**：系統結合圖片風格 + 自然語言條件推薦商品
4. **探索搭配**：點擊商品查看可搭配的其他單品

## 主要功能模組

### 資料載入器（Loaders）

- `loader/instagram_neo4j.py`：抓取 Instagram 穿搭貼文，建立 User, Post, Style 節點
- `loader/shop_neo4j.py`：載入商品資料，建立 Product, Brand, Category, Style 關係

### 查詢引擎（Query）

- `query/query_neo4j.py`：核心推薦引擎
  - 圖片 → 風格預測（向量相似度搜尋）
  - 自然語言 → Cypher 查詢
  - 混合推薦（圖關係 + 向量搜尋）

### 資料庫管理（Database）

- `database/init_neo4j_schema.py`：初始化 Neo4j schema

### API 服務器

- `server.py`：Flask API，提供 `/api/search` 端點

## 開發指令

```bash
# 測試查詢引擎
python query/query_neo4j.py

# 檢查 Neo4j 資料
# 在 Neo4j Browser (http://localhost:7474) 執行：
MATCH (n) RETURN labels(n), count(n)  # 查看節點統計
MATCH ()-[r]->() RETURN type(r), count(r)  # 查看關係統計
```

## 常見問題

**Q: Port 8000 被占用？**
A: 修改 `.env` 中的 `SERVER_PORT`，並同步更新前端 `ui/src/config/chat.ts` 的 `BASE_URL`

**Q: 圖片上傳失敗？**
A: 檢查圖片大小是否超過 15MB，建議壓縮後上傳

**Q: 找不到商品？**
A: 確保已執行 `python loader/shop_neo4j.py` 載入商品資料

**Q: Neo4j 連線失敗？**
A: 確認 Neo4j 服務已啟動，檢查 `.env` 中的連線資訊

## 專案結構

```
OutfitMatch/
├── OutfitMatch/              # 後端
│   ├── config/              # 配置文件
│   ├── database/            # 資料庫初始化
│   ├── loader/              # 資料載入器
│   ├── query/               # 查詢引擎
│   ├── data/                # CSV 資料
│   ├── test/images/         # 測試圖片
│   └── server.py            # API 服務器
├── ui/                      # 前端
│   └── src/
│       ├── components/      # React 組件
│       ├── services/        # API 服務
│       └── config/          # 前端配置
├── ARCHITECTURE.md          # 架構設計文檔
└── README.md               # 本文件
```

## 下一步開發

- [ ] 實作商品搭配關係自動建立
- [ ] 加入用戶喜好學習
- [ ] 支援多圖片比較
- [ ] 優化 LLM 查詢快取
- [ ] 增加單元測試

## License

MIT
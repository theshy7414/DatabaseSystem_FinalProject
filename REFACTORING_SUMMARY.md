# OutfitMatch 重構總結報告

**重構日期**：2025年12月30日  
**目標**：將 OutfitMatch 從混合資料庫架構重構為基於 Neo4j 圖資料庫的智能推薦系統

## 📋 完成的重構項目

### ✅ 1. 創建配置文件和環境設定

**新增檔案**：
- `OutfitMatch/config/__init__.py` - 配置模組
- `OutfitMatch/config/settings.example.py` - 配置範本（包含所有設定項目）
- `OutfitMatch/.env.example` - 環境變數範本
- `OutfitMatch/config/settings.py` - 實際配置檔（已生成）

**改進點**：
- 統一使用 `python-dotenv` 載入環境變數
- 支援自定義 LLM 模型（降低成本）
- 支援快取配置
- 清晰的配置文檔

### ✅ 2. 設計新的 Neo4j Schema

**新增檔案**：
- `ARCHITECTURE.md` - 完整架構設計文檔

**圖資料庫設計**：

#### 節點類型（7種）
1. **User** - 用戶/Instagram 創作者
2. **Post** - Instagram 穿搭貼文（包含圖片 embedding）
3. **Product** - 商品
4. **Style** - 風格標籤（日系、韓系等 16 種）
5. **Brand** - 品牌
6. **Category** - 類別（上衣、下身、連身、配件、其他）
7. **Item** - 單品（從貼文中提取）

#### 關係類型（11種）
1. `User -[:POSTED]-> Post` - 用戶發布貼文
2. `Post -[:HAS_STYLE {confidence}]-> Style` - 貼文的風格
3. `Post -[:MENTIONS_ITEM]-> Item` - 貼文提到的單品
4. `Product -[:HAS_STYLE {confidence}]-> Style` - 商品的風格
5. `Product -[:OF_BRAND]-> Brand` - 商品的品牌
6. `Product -[:IN_CATEGORY]-> Category` - 商品的類別
7. `Item -[:OF_BRAND]-> Brand` - 單品的品牌
8. **`Product -[:GOES_WITH {score, style_match}]-> Product`** - 商品搭配推薦 ⭐
9. **`Product -[:INSPIRED_BY {similarity}]-> Post`** - 商品與貼文的關聯 ⭐
10. `Style -[:SIMILAR_TO {similarity}]-> Style` - 風格相似度
11. `User -[:LIKED]-> Post` - 用戶喜好（未來擴展）

#### 向量索引
- `post_image_index` - 貼文圖片 embedding（768維，cosine similarity）
- `product_image_index` - 商品圖片 embedding（768維，cosine similarity）

### ✅ 3. 重構商品資料載入器

**新增檔案**：
- `OutfitMatch/loader/shop_neo4j.py` - 替代原本的 `shop_postgres.py`

**功能改進**：
- 將商品資料載入 Neo4j（而非 PostgreSQL）
- 自動建立 Product, Brand, Category 節點
- 自動建立商品與風格的關係（HAS_STYLE）
- 批次處理 LLM 風格預測
- 詳細的進度日誌和錯誤處理
- 支援參數：`--nrows`（測試用）、`--skip_prediction`（跳過 LLM）

### ✅ 4. 建立資料庫初始化腳本

**新增檔案**：
- `OutfitMatch/database/init_neo4j_schema.py`

**功能**：
- 自動創建所有必要的約束（Constraints）
- 創建效能索引（價格、名稱、時間等）
- 創建全文搜索索引
- 創建向量索引
- 初始化基礎資料（16種風格、5種類別）
- 驗證設置

### ✅ 5. 實作圖關係推薦引擎

**新增檔案**：
- `OutfitMatch/query/query_neo4j.py` - 替代原本的 `query/query.py`

**核心功能**：

#### a) 圖片相似度搜尋
```python
def image_to_styles(query_image) -> List[str]:
    # 1. 分割時尚區域 (Segformer)
    # 2. 生成 embedding (DINOv2)
    # 3. 在 Neo4j 向量索引中搜尋相似貼文
    # 4. 返回該貼文的風格標籤
```

#### b) 自然語言 → Cypher 轉換
```python
def nl_to_cypher_conditions(nl_query: str) -> str:
    # 使用 GPT-4o 將「2000元以下的韓系上衣」
    # 轉換為 "p.price <= 2000 AND c.name = '上衣' AND s.name = '韓系'"
```

#### c) 混合推薦查詢
```python
def search_products_by_style_and_conditions():
    # 結合：
    # 1. 圖片推測的風格
    # 2. 自然語言的條件
    # 3. 圖關係查詢
    # 執行 Cypher 查詢獲得推薦
```

#### d) 商品搭配推薦
```python
def get_matching_products_for_product():
    # 基於 GOES_WITH 關係推薦可搭配商品
    # 考慮：相同風格、不同類別、價格合理性
```

### ✅ 6. 建立推薦關係建構器

**新增檔案**：
- `OutfitMatch/database/build_relationships.py`

**功能**：
1. **風格基礎推薦** - 找相同風格但不同類別的商品，創建 `GOES_WITH` 關係
2. **完整穿搭推薦** - 特別處理上衣+下身組合
3. **貼文啟發關係** - 連接商品與相似風格的 Instagram 貼文
4. **風格相似圖** - 分析風格之間的共現關係
5. **推薦網路分析** - 統計和報告推薦關係的品質

### ✅ 7. 更新 API 服務器

**修改檔案**：
- `OutfitMatch/server.py`

**改進點**：
- 引入 `query_neo4j` 而非 `query`
- 使用 Neo4j 連線池（不再每次請求後關閉連線）
- 從 `config.settings` 讀取 `SERVER_PORT`
- 改善錯誤處理（檢查 `result.get('products')`）
- 統一返回格式

### ✅ 8. 修復前後端對接

**修改檔案**：
- `ui/src/config/chat.ts`

**改進點**：
- 修正 `BASE_URL` 從 `localhost:5000` → `localhost:8000`
- 統一 API 端點 `/api/search`
- 前後端 port 一致

### ✅ 9. 更新文檔

**新增/更新檔案**：
- `README.md` - 完全重寫，清晰的使用指南
- `ARCHITECTURE.md` - 詳細的架構設計文檔
- `QUICKSTART.md` - 15分鐘快速開始指南

## 📊 架構對比

| 項目 | 舊架構 | 新架構 |
|------|--------|--------|
| **資料庫** | Neo4j + PostgreSQL | 純 Neo4j |
| **商品儲存** | PostgreSQL | Neo4j (Product 節點) |
| **風格關聯** | ❌ 無關聯 | ✅ HAS_STYLE 關係 |
| **推薦邏輯** | ❌ SQL 篩選 | ✅ 圖遍歷 + 向量搜尋 |
| **圖片搜尋** | ❌ 未使用向量索引 | ✅ Neo4j 向量索引 |
| **商品搭配** | ❌ 不支援 | ✅ GOES_WITH 關係 |
| **穿搭靈感** | ❌ 斷層 | ✅ INSPIRED_BY 關係 |
| **資料庫連線** | 每次請求重連 | 連線池 |
| **配置管理** | ❌ 缺失 settings.py | ✅ 完整配置系統 |
| **文檔** | 簡陋 | 完整（3份文檔） |

## 🎯 核心改進

### 1. 真正利用 Neo4j 的圖關係

**舊架構的問題**：
```
Instagram 貼文 (Neo4j) ❌ 無連接 ❌ 商品 (PostgreSQL)
```

**新架構**：
```
Instagram貼文 -[HAS_STYLE]-> 風格 <-[HAS_STYLE]- 商品
商品 -[GOES_WITH]-> 商品 (搭配推薦)
商品 -[INSPIRED_BY]-> 貼文 (穿搭靈感)
```

### 2. 向量 + 圖混合搜尋

**查詢流程**：
```
用戶上傳圖片
    ↓
生成 embedding
    ↓
向量索引找相似 Instagram 貼文 (db.index.vector.queryNodes)
    ↓
獲取貼文的風格標籤
    ↓
基於風格遍歷圖找商品 (MATCH ... WHERE)
    ↓
考慮價格、類別等條件篩選
    ↓
返回推薦結果 + 穿搭靈感圖片
```

### 3. 多維度推薦

1. **風格相似推薦** - 基於 HAS_STYLE 關係
2. **商品搭配推薦** - 基於 GOES_WITH 關係
3. **穿搭靈感推薦** - 基於 INSPIRED_BY 關係
4. **圖片相似推薦** - 基於向量索引

## 🚀 使用流程

### 完整部署流程

```bash
# 1. 環境設置
cd OutfitMatch
cp .env.example .env
# 編輯 .env 填入憑證

# 2. 安裝依賴
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. 初始化資料庫
python database/init_neo4j_schema.py

# 4. 載入商品資料
python loader/shop_neo4j.py --nrows 100  # 測試用

# 5. 載入 Instagram 資料（可選）
python loader/instagram_neo4j.py --max_posts 20

# 6. 建立推薦關係
python database/build_relationships.py

# 7. 啟動服務
python server.py

# 8. 啟動前端（新終端）
cd ui
npm install
npm run dev
```

### 查詢範例

**Cypher 查詢範例**（可在 Neo4j Browser 測試）：

```cypher
// 1. 查看資料統計
MATCH (n) RETURN labels(n)[0] as type, count(n) as count

// 2. 查看推薦關係
MATCH (p1:Product)-[r:GOES_WITH]->(p2:Product)
RETURN p1.name, p2.name, r.score, r.common_styles
ORDER BY r.score DESC
LIMIT 10

// 3. 查找完整穿搭
MATCH (top:Product)-[:IN_CATEGORY]->(:Category {name: '上衣'})
MATCH (top)-[:GOES_WITH]->(bottom:Product)-[:IN_CATEGORY]->(:Category {name: '下身'})
MATCH (top)-[:HAS_STYLE]->(s:Style {name: '韓系'})
MATCH (bottom)-[:HAS_STYLE]->(s)
RETURN top.name, bottom.name, top.price + bottom.price as total_price
ORDER BY total_price ASC
LIMIT 5

// 4. 從 Instagram 貼文找商品
MATCH (post:Post)-[:HAS_STYLE]->(s:Style {name: '日系'})
MATCH (product:Product)-[:INSPIRED_BY]->(post)
RETURN product.name, product.price, post.image as inspiration
LIMIT 10
```

## 📝 待完成項目

根據待辦清單，還有以下項目需要處理：

### 🔶 中優先級
- [ ] **優化 LLM 呼叫策略**（任務 #7）
  - 實作查詢快取
  - 批次處理風格預測
  - 考慮使用更便宜的模型

- [ ] **重構圖片處理**（任務 #8）
  - 統一模型管理（避免重複載入）
  - 建立 pipeline
  - 改善錯誤處理

- [ ] **移除 PostgreSQL 依賴**（任務 #6）
  - 從 requirements.txt 移除 psycopg2
  - 刪除 loader/shop_postgres.py（已被 shop_neo4j.py 取代）
  - 清理所有 PostgreSQL 相關程式碼

### 🔷 低優先級
- [ ] **建立測試和文檔**（任務 #10）
  - 單元測試
  - 整合測試
  - API 文檔

## 🎓 學習資源

### Neo4j Cypher 查詢語法
- [Neo4j Cypher 官方文檔](https://neo4j.com/docs/cypher-manual/current/)
- [圖資料庫模式設計](https://neo4j.com/developer/graph-data-modeling/)

### 向量搜尋
- [Neo4j Vector Index](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)

### 推薦範例查詢
詳見 `ARCHITECTURE.md` 中的「核心查詢場景」章節

## 💡 未來擴展建議

1. **用戶喜好學習**
   - 記錄用戶點擊的商品
   - 建立 `User -[:LIKED]-> Product` 關係
   - 基於協同過濾推薦

2. **季節性推薦**
   - 為商品和風格添加 `season` 屬性
   - 根據當前季節調整推薦權重

3. **價格區間智能調整**
   - 分析用戶購買力
   - 動態調整推薦商品價格範圍

4. **多圖片比較**
   - 支援上傳多張參考圖片
   - 融合多個 embedding 進行搜尋

5. **社交功能**
   - 讓用戶分享穿搭組合
   - 建立穿搭社群圖譜

## 🏆 總結

這次重構成功地將 OutfitMatch 從一個概念驗證專案，轉變為一個**真正利用圖資料庫能力**的智能推薦系統。

**主要成就**：
- ✅ 統一資料庫架構（Neo4j）
- ✅ 建立完整的圖關係模型
- ✅ 實現向量 + 圖混合搜尋
- ✅ 支援多維度推薦
- ✅ 完整的文檔和配置系統
- ✅ 可擴展的架構設計

**預計完成時間**：按照現在的進度，剩餘優化項目約需 1-2 週完成。

祝專案成功！🎉

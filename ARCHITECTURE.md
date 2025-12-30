# OutfitMatch 架構設計文檔

## 專案概述
OutfitMatch 是一個基於圖資料庫的智能穿搭推薦系統，結合：
- Instagram 穿搭圖片分析
- 商品風格標籤
- 圖神經網路關係推薦

## 新架構設計（Neo4j 為核心）

### 資料庫架構
**統一使用 Neo4j** 作為唯一資料庫，充分利用圖關係查詢優勢。

#### 節點類型 (Nodes)

```cypher
// 1. 用戶節點
(:User {
  id: String,
  name: String,
  instagram_handle: String
})

// 2. 穿搭貼文節點
(:Post {
  id: String,
  url: String,
  caption: Text,
  description: Text,
  image_url: String,
  img_embedding: Vector[768],  // DINOv2 embedding
  timestamp: DateTime
})

// 3. 商品節點
(:Product {
  id: String,
  name: String,
  description: Text,
  price: Float,
  original_price: Float,
  image_url: String,
  img_embedding: Vector[768],  // 可選：商品圖片 embedding
  created_at: DateTime
})

// 4. 風格節點
(:Style {
  name: String,  // 日系、韓系、歐美、街頭等
  description: Text
})

// 5. 品牌節點
(:Brand {
  name: String,
  country: String
})

// 6. 類別節點
(:Category {
  name: String,  // 上衣、下身、連身、配件、其他
  parent: String  // 可選：支援子分類
})

// 7. 單品節點（從 Instagram 貼文提取）
(:Item {
  name: String,  // "Top:Zara"
  type: String   // Top, Pants, Shoes 等
})
```

#### 關係類型 (Relationships)

```cypher
// 用戶與貼文
(:User)-[:POSTED]->(:Post)
(:User)-[:LIKED]->(:Post)  // 未來擴展：用戶喜好
(:User)-[:VIEWED]->(:Post)  // 未來擴展：瀏覽歷史

// 貼文與風格
(:Post)-[:HAS_STYLE {confidence: Float}]->(:Style)
(:Post)-[:MENTIONS_ITEM]->(:Item)

// 商品與屬性
(:Product)-[:HAS_STYLE {confidence: Float}]->(:Style)
(:Product)-[:OF_BRAND]->(:Brand)
(:Product)-[:IN_CATEGORY]->(:Category)

// 單品與品牌
(:Item)-[:OF_BRAND]->(:Brand)

// 商品搭配推薦（核心關係）
(:Product)-[:GOES_WITH {
  score: Float,        // 搭配分數
  style_match: Float,  // 風格契合度
  occasion: String     // 場合：casual, formal, sport
}]->(:Product)

// 風格相似（自動生成）
(:Style)-[:SIMILAR_TO {similarity: Float}]->(:Style)

// 商品與貼文關聯（基於風格）
(:Product)-[:INSPIRED_BY {similarity: Float}]->(:Post)
```

### 向量索引

```cypher
// 為圖片 embedding 創建向量索引
CREATE VECTOR INDEX post_image_index IF NOT EXISTS
FOR (p:Post)
ON p.img_embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};

CREATE VECTOR INDEX product_image_index IF NOT EXISTS
FOR (p:Product)
ON p.img_embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
```

### 核心查詢場景

#### 1. 圖片相似搭配推薦
```cypher
// 用戶上傳圖片 → 找相似的 Instagram 貼文 → 推薦相同風格商品
CALL db.index.vector.queryNodes(
  'post_image_index', 
  3, 
  $query_embedding
) YIELD node AS similar_post, score

MATCH (similar_post)-[:HAS_STYLE]->(style)
MATCH (product:Product)-[:HAS_STYLE]->(style)
WHERE product.price <= $max_price

RETURN product, style, 
       score AS image_similarity,
       similar_post.image_url AS inspiration_image
ORDER BY score DESC, product.price ASC
LIMIT 10
```

#### 2. 風格基礎推薦 + 自然語言篩選
```cypher
// 用戶查詢：「2000元以下的韓系上衣」
MATCH (product:Product)-[:HAS_STYLE]->(style:Style {name: '韓系'})
MATCH (product)-[:IN_CATEGORY]->(cat:Category {name: '上衣'})
WHERE product.price <= 2000

// 找出相關的穿搭靈感
OPTIONAL MATCH (product)-[:HAS_STYLE]->(style)<-[:HAS_STYLE]-(post:Post)

RETURN product, 
       collect(DISTINCT style.name) AS styles,
       collect(DISTINCT post.image_url)[..3] AS inspiration_images
ORDER BY product.price ASC
LIMIT 10
```

#### 3. 商品搭配推薦（利用圖關係）
```cypher
// 用戶選擇了一件商品 → 推薦可以搭配的其他商品
MATCH (selected:Product {id: $product_id})
MATCH (selected)-[:HAS_STYLE]->(style)

// 方案 A：直接搭配關係
MATCH (selected)-[:GOES_WITH]->(match:Product)
RETURN match, 'direct_match' AS match_type
ORDER BY match.score DESC

UNION

// 方案 B：相同風格的不同類別商品
MATCH (match:Product)-[:HAS_STYLE]->(style)
MATCH (match)-[:IN_CATEGORY]->(cat)
WHERE match.id <> selected.id
  AND NOT (selected)-[:IN_CATEGORY]->(cat)  // 不同類別
RETURN match, 'style_match' AS match_type
ORDER BY match.price ASC

LIMIT 10
```

#### 4. 穿搭靈感探索
```cypher
// 從熱門穿搭貼文發現商品
MATCH (post:Post)-[:HAS_STYLE]->(style:Style {name: $style_name})
MATCH (post)-[:MENTIONS_ITEM]->(item)-[:OF_BRAND]->(brand)

// 找到類似品牌的可購買商品
MATCH (product:Product)-[:OF_BRAND]->(brand)
MATCH (product)-[:HAS_STYLE]->(style)

RETURN post, product, brand
ORDER BY post.timestamp DESC
LIMIT 20
```

### 資料流程

#### 階段 1：資料載入
```
1. Instagram 爬蟲 (instagram_neo4j.py)
   └─> 創建 User, Post, Item, Brand 節點
   └─> 生成圖片 embedding
   └─> LLM 推測風格 → 創建 HAS_STYLE 關係

2. 商品資料載入 (shop_neo4j.py)
   └─> 創建 Product, Brand, Category 節點
   └─> LLM 推測商品風格 → 創建 HAS_STYLE 關係
   └─> （可選）生成商品圖片 embedding
```

#### 階段 2：關係建立
```
3. 風格關聯 (build_relationships.py)
   └─> 分析 Post 和 Product 的共同風格
   └─> 創建 INSPIRED_BY 關係
   └─> 基於圖片相似度創建 SIMILAR_TO 關係

4. 商品搭配關係 (build_recommendations.py)
   └─> 分析成功的穿搭組合
   └─> 創建 GOES_WITH 關係
   └─> 計算搭配分數
```

#### 階段 3：查詢服務
```
5. API Server (server.py)
   └─> 接收用戶查詢 + 圖片
   └─> NL → Cypher 轉換
   └─> 執行圖查詢
   └─> 返回商品 + 穿搭靈感
```

## 技術優勢

### 使用 Neo4j 的好處
1. **多跳關係查詢**：輕鬆實現「找相似風格的相似搭配」
2. **動態推薦**：基於圖結構的協同過濾
3. **向量 + 圖混合搜尋**：圖片相似 + 關係推薦結合
4. **可解釋性**：可追溯推薦路徑 (Post → Style → Product)

### 與舊架構對比
| 功能 | 舊架構 (Neo4j + PostgreSQL) | 新架構 (純 Neo4j) |
|------|----------------------------|-------------------|
| 資料儲存 | 分散在兩個資料庫 | 統一在 Neo4j |
| 向量搜尋 | 未使用 | 使用 vector index |
| 關係推薦 | ❌ 不支援 | ✅ 核心功能 |
| 風格關聯 | ❌ 斷層 | ✅ 直接連接 |
| 查詢效能 | 需要跨庫查詢 | 單一 Cypher 查詢 |

## 下一步實施計劃

### Week 1: 基礎重構
- [x] 創建配置文件
- [ ] 設計 Neo4j schema
- [ ] 重寫 shop_neo4j.py

### Week 2: 關係建立
- [ ] 實作風格關聯邏輯
- [ ] 創建商品搭配關係
- [ ] 優化向量索引

### Week 3: 查詢引擎
- [ ] NL to Cypher
- [ ] 混合查詢（向量+圖）
- [ ] 快取機制

### Week 4: 優化與測試
- [ ] 效能調優
- [ ] 整合測試
- [ ] 文檔更新

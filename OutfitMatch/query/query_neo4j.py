"""
Neo4j Query Engine
基於圖關係的智能推薦查詢引擎
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
from neo4j import GraphDatabase
import numpy as np
from PIL import Image
import base64
from io import BytesIO
import logging
from typing import List, Dict, Tuple, Optional
from config.settings import (
    OPENAI_API_KEY,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NL2CYPHER_MODEL
)
from loader.instagram_neo4j import (
    segment_and_crop_fashion,
    get_image_embedding
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Neo4j driver (use connection pool)
driver = None


def init_neo4j():
    """初始化 Neo4j 連線池"""
    global driver
    if driver is None:
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50
        )
        logger.info("✅ Connected to Neo4j with connection pool")


def close_neo4j():
    """關閉 Neo4j 連線"""
    global driver
    if driver is not None:
        driver.close()
        driver = None
        logger.info("🔌 Disconnected from Neo4j")


def nl_to_cypher_conditions(nl_query: str) -> str:
    """
    將自然語言轉換為 Cypher WHERE 條件
    使用 LLM 進行轉換
    """
    prompt_template = """
你是一個 Neo4j Cypher 專家。根據下列圖資料庫結構，將用戶的自然語言問題轉換成 Cypher 的 WHERE 條件。

圖資料庫結構：
- (:Product)-[:OF_BRAND]->(:Brand)
- (:Product)-[:IN_CATEGORY]->(:Category)
- (:Product)-[:HAS_STYLE]->(:Style)

Product 屬性: name, description, price, original_price, image_url
Category 類別: 上衣、下身、連身、配件、其他
Style 風格: 日系、韓系、歐美、街頭、簡約、運動風、復古、休閒、工裝、優雅、戶外、都會、甜美、性感、正裝、華麗

要求：
1. 只返回 WHERE 條件部分（不要 MATCH、RETURN）
2. 使用變數名 p（Product）、b（Brand）、c（Category）、s（Style）
3. 價格條件使用 p.price
4. 品牌條件使用 b.name
5. 類別條件使用 c.name
6. 風格條件使用 s.name
7. 全部寫在一行，不要換行
8. 不要用 markdown code block

範例：
問題：「三千元以下的Nike鞋子」
答案：b.name = 'Nike' AND p.price <= 3000 AND c.name = '配件'

問題：「2000元以下的韓系上衣」
答案：p.price <= 2000 AND c.name = '上衣' AND s.name = '韓系'

問題：「1000元以下的休閒褲子」
答案：p.price <= 1000 AND c.name = '下身' AND s.name = '休閒'

現在請處理：
問題：{query}
答案：
"""
    
    full_prompt = prompt_template.format(query=nl_query)
    
    try:
        resp = client.chat.completions.create(
            model=NL2CYPHER_MODEL,
            messages=[
                {"role": "system", "content": "你是 Neo4j Cypher 查詢專家"},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1
        )
        conditions = resp.choices[0].message.content.strip()
        # 移除可能的 markdown 標記
        conditions = conditions.replace('```', '').replace('cypher', '').strip()
        logger.info(f"📝 NL to Cypher: {nl_query} -> {conditions}")
        return conditions
    except Exception as e:
        logger.error(f"Error in NL to Cypher conversion: {e}")
        return "TRUE"  # 返回總是為真的條件作為後備


def image_to_styles(query_image) -> List[str]:
    """
    從上傳的圖片推測風格
    1. 在 Neo4j 中找最相似的 Instagram 貼文
    2. 獲取該貼文的風格標籤
    """
    try:
        init_neo4j()
        
        logger.info(f"Processing image type: {type(query_image)}")
        
        # 處理不同格式的圖片輸入
        if isinstance(query_image, str):
            if query_image.startswith('data:image') or query_image.startswith('/9j/') or query_image.startswith('iVBOR'):
                # Base64 編碼的圖片
                base64_data = query_image.split(',')[1] if ',' in query_image else query_image
                img_data = base64.b64decode(base64_data)
                img = Image.open(BytesIO(img_data))
            elif os.path.isfile(query_image):
                # 文件路徑
                img = Image.open(query_image)
            else:
                raise ValueError(f"Invalid image string format")
        elif isinstance(query_image, Image.Image):
            img = query_image
        else:
            raise ValueError(f"Invalid image type: {type(query_image)}")
        
        logger.info(f"Image loaded: {img.size} {img.mode}")
        
        # 分割時尚區域並生成 embedding
        seg_img = segment_and_crop_fashion(img)
        query_emb = get_image_embedding(seg_img)
        
        logger.info(f"Generated embedding: shape {query_emb.shape}")
        
        # 在 Neo4j 中找相似的貼文
        with driver.session() as session:
            # 使用向量索引搜尋
            result = session.run("""
                CALL db.index.vector.queryNodes('post_image_index', 3, $embedding)
                YIELD node, score
                MATCH (node)-[:HAS_STYLE]->(style:Style)
                RETURN node.id as post_id, 
                       node.description as description,
                       collect(DISTINCT style.name) as styles,
                       score
                ORDER BY score DESC
                LIMIT 1
            """, embedding=query_emb.tolist())
            
            record = result.single()
            
            if record:
                styles = record['styles']
                logger.info(f"🎨 Found similar post with styles: {styles} (similarity: {record['score']:.3f})")
                return styles if styles else ['休閒']
            else:
                logger.warning("No similar posts found, using default style")
                return ['休閒']
                
    except Exception as e:
        logger.error(f"Error in image_to_styles: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ['休閒']  # 返回預設風格


def search_products_by_style_and_conditions(
    styles: List[str], 
    cypher_conditions: str, 
    limit: int = 10
) -> List[Tuple]:
    """
    基於風格和條件搜尋商品（使用圖關係）
    """
    init_neo4j()
    
    with driver.session() as session:
        # 精確匹配：所有風格都符合
        exact_query = f"""
        MATCH (p:Product)-[:HAS_STYLE]->(s:Style)
        WHERE s.name IN $styles
        MATCH (p)-[:OF_BRAND]->(b:Brand)
        MATCH (p)-[:IN_CATEGORY]->(c:Category)
        WHERE {cypher_conditions}
        WITH p, b, c, collect(DISTINCT s.name) as product_styles
        WHERE size(product_styles) = size($styles)
        RETURN p.id as id, p.name as name, p.description as description,
               c.name as category, b.name as brand, p.price as price,
               product_styles as predicted_style, p.image_url as image_url
        ORDER BY p.price ASC
        LIMIT $limit
        """
        
        try:
            result = session.run(exact_query, styles=styles, limit=limit)
            products = [(r['id'], r['name'], r['description'], r['category'], 
                        r['brand'], r['price'], r['predicted_style'], r['image_url']) 
                       for r in result]
            
            if products:
                logger.info(f"✅ Found {len(products)} products with exact style match")
                return products
        except Exception as e:
            logger.error(f"Error in exact match query: {e}")
        
        # 部分匹配：至少有一個風格符合
        partial_query = f"""
        MATCH (p:Product)-[:HAS_STYLE]->(s:Style)
        WHERE s.name IN $styles
        MATCH (p)-[:OF_BRAND]->(b:Brand)
        MATCH (p)-[:IN_CATEGORY]->(c:Category)
        WHERE {cypher_conditions}
        WITH p, b, c, collect(DISTINCT s.name) as product_styles, count(s) as style_matches
        RETURN p.id as id, p.name as name, p.description as description,
               c.name as category, b.name as brand, p.price as price,
               product_styles as predicted_style, p.image_url as image_url
        ORDER BY style_matches DESC, p.price ASC
        LIMIT $limit
        """
        
        try:
            result = session.run(partial_query, styles=styles, limit=limit)
            products = [(r['id'], r['name'], r['description'], r['category'], 
                        r['brand'], r['price'], r['predicted_style'], r['image_url']) 
                       for r in result]
            
            logger.info(f"✅ Found {len(products)} products with partial style match")
            return products
        except Exception as e:
            logger.error(f"Error in partial match query: {e}")
            return []


def get_matching_products_for_product(product_id: str, limit: int = 5) -> List[Tuple]:
    """
    為指定商品推薦搭配商品
    基於：1) 相同風格 2) 不同類別
    """
    init_neo4j()
    
    with driver.session() as session:
        query = """
        MATCH (selected:Product {id: $product_id})
        MATCH (selected)-[:HAS_STYLE]->(style:Style)
        MATCH (selected)-[:IN_CATEGORY]->(selected_cat:Category)
        
        // 找相同風格但不同類別的商品
        MATCH (match:Product)-[:HAS_STYLE]->(style)
        MATCH (match)-[:IN_CATEGORY]->(match_cat:Category)
        WHERE match.id <> selected.id 
          AND match_cat.name <> selected_cat.name
        
        MATCH (match)-[:OF_BRAND]->(b:Brand)
        
        WITH match, b, match_cat, 
             collect(DISTINCT style.name) as styles,
             count(DISTINCT style) as common_styles
        
        RETURN match.id as id, match.name as name, match.description as description,
               match_cat.name as category, b.name as brand, match.price as price,
               styles as predicted_style, match.image_url as image_url
        ORDER BY common_styles DESC, match.price ASC
        LIMIT $limit
        """
        
        result = session.run(query, product_id=product_id, limit=limit)
        products = [(r['id'], r['name'], r['description'], r['category'], 
                    r['brand'], r['price'], r['predicted_style'], r['image_url']) 
                   for r in result]
        
        logger.info(f"✅ Found {len(products)} matching products for {product_id}")
        return products


def user_query(query_text: str, query_image) -> Dict:
    """
    用戶查詢的主入口
    結合自然語言 + 圖片進行智能推薦
    """
    try:
        # 1. 將自然語言轉換為 Cypher 條件
        cypher_conditions = nl_to_cypher_conditions(query_text)
        
        # 2. 從圖片推測風格
        styles = image_to_styles(query_image)
        
        # 3. 基於風格和條件搜尋商品
        products = search_products_by_style_and_conditions(styles, cypher_conditions, limit=10)
        
        if products:
            response_text = f"您上傳的圖片最接近 {' + '.join(styles)} 風格，以下是符合您條件的商品："
        else:
            response_text = "抱歉，找不到符合條件的商品。試試放寬條件或更換圖片吧！"
        
        return {
            "text": response_text,
            "products": products,
            "detected_styles": styles
        }
        
    except Exception as e:
        logger.error(f"Error in user_query: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "text": f"查詢時發生錯誤：{str(e)}",
            "products": [],
            "detected_styles": []
        }


# 初始化連線
init_neo4j()


if __name__ == "__main__":
    # 測試查詢
    try:
        print("\n🧪 Test 1: 2000元以下的上衣")
        result = user_query("2000元以下的上衣", "test/images/top.jpg")
        print(f"Results: {len(result['products'])} products")
        for p in result['products'][:3]:
            print(f"  - {p[1]} (${p[5]}) - {p[4]} | {p[3]}")
        
        print("\n🧪 Test 2: 韓系洋裝")
        result = user_query("韓系洋裝", "test/images/top.jpg")
        print(f"Results: {len(result['products'])} products")
        
    finally:
        close_neo4j()

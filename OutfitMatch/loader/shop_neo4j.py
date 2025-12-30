"""
Shop Data Loader for Neo4j
將商品資料載入 Neo4j 圖資料庫，建立與風格、品牌、類別的關係
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import openai
from neo4j import GraphDatabase
import ast
import time
import argparse
import logging
from typing import List, Dict
from config.settings import (
    OPENAI_API_KEY,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    STYLE_PREDICTION_MODEL
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize Neo4j driver
driver = None

STYLE_LIST = "日系、韓系、歐美、街頭、簡約、運動風、復古、休閒、工裝、優雅、戶外、都會、甜美、性感、正裝、華麗"

PROMPT = """
你是一個時尚穿搭風格專家。根據以下資訊，請判斷這項商品最符合的 1~2 個風格（從下列風格選，最多2個），只回傳 Python list 格式，不需解釋、不需補充。
可選風格有：{style_list}
請用 ['風格1', '風格2'] 或 ['風格1'] 格式回傳，不要有多餘文字。

---
商品名稱：{item}
商品描述：{desc}
類別：{category}
品牌：{brand}
---
"""


def init_neo4j():
    """初始化 Neo4j 連線"""
    global driver
    if driver is None:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        logger.info("✅ Connected to Neo4j")


def close_neo4j():
    """關閉 Neo4j 連線"""
    global driver
    if driver is not None:
        driver.close()
        driver = None
        logger.info("🔌 Disconnected from Neo4j")


def predict_style(row: pd.Series) -> str:
    """使用 LLM 預測商品風格"""
    prompt = PROMPT.format(
        style_list=STYLE_LIST,
        item=row['name'],
        desc=row['description'],
        category=row.get('category', '未知'),
        brand=row.get('brand', '未知')
    )
    
    for retry in range(3):
        try:
            resp = client.chat.completions.create(
                model=STYLE_PREDICTION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error predicting style (attempt {retry + 1}/3): {e}")
            time.sleep(2)
    return "[]"


def process_products(products_csv: str, products_csv_with_style: str, 
                    nrows: int = None, skip_prediction: bool = False) -> pd.DataFrame:
    """處理商品資料並預測風格"""
    
    if skip_prediction and os.path.exists(products_csv_with_style):
        logger.info("📄 Skip prediction mode: Reading existing processed CSV")
        df = pd.read_csv(products_csv_with_style, nrows=nrows)
    else:
        logger.info("📄 Reading original CSV and predicting styles")
        df = pd.read_csv(products_csv, nrows=nrows)
        
        # 批次處理風格預測
        logger.info(f"🔮 Predicting styles for {len(df)} products...")
        df['predicted_style'] = df.apply(predict_style, axis=1)
        
        # 儲存結果
        df.to_csv(products_csv_with_style, index=False)
        logger.info(f"💾 Style prediction completed and saved to {products_csv_with_style}")
    
    return df


def create_product_node(tx, product_data: Dict):
    """在 Neo4j 中創建商品節點及其關係"""
    
    # 創建商品節點
    query = """
    MERGE (p:Product {id: $id})
    SET p.name = $name,
        p.description = $description,
        p.price = $price,
        p.original_price = $original_price,
        p.image_url = $image_url,
        p.created_at = datetime()
    
    // 創建品牌關係
    MERGE (b:Brand {name: $brand})
    MERGE (p)-[:OF_BRAND]->(b)
    
    // 創建類別關係
    MERGE (c:Category {name: $category})
    MERGE (p)-[:IN_CATEGORY]->(c)
    
    RETURN p.id as product_id
    """
    
    result = tx.run(query, **product_data)
    return result.single()['product_id']


def create_style_relationships(tx, product_id: str, styles: List[str]):
    """創建商品與風格的關係"""
    
    query = """
    MATCH (p:Product {id: $product_id})
    UNWIND $styles as style_name
    MERGE (s:Style {name: style_name})
    MERGE (p)-[r:HAS_STYLE]->(s)
    SET r.confidence = 0.8
    RETURN count(r) as relationships_created
    """
    
    result = tx.run(query, product_id=product_id, styles=styles)
    return result.single()['relationships_created']


def import_to_neo4j(df: pd.DataFrame):
    """將商品資料匯入 Neo4j"""
    
    init_neo4j()
    
    total_rows = len(df)
    imported_rows = 0
    skipped_rows = 0
    
    logger.info(f"🚀 Starting import of {total_rows} products to Neo4j...")
    
    with driver.session() as session:
        for idx, row in df.iterrows():
            try:
                # 解析預測的風格
                try:
                    styles = ast.literal_eval(row['predicted_style'])
                    if not isinstance(styles, list):
                        raise ValueError("predicted_style must be a list")
                    # 過濾無效風格
                    valid_styles = [s for s in styles if s in STYLE_LIST]
                    if not valid_styles:
                        valid_styles = ['其他']
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Invalid predicted_style at row {idx}: {e}, using default")
                    valid_styles = ['休閒']
                
                # 準備商品資料
                product_data = {
                    'id': f"prod_{idx}",  # 生成唯一 ID
                    'name': str(row['name']),
                    'description': str(row['description']),
                    'category': str(row.get('category', '其他')),
                    'brand': str(row.get('brand', '未知品牌')),
                    'price': float(row['price']) if pd.notna(row['price']) else 0.0,
                    'original_price': float(row.get('original_price', row['price'])) if pd.notna(row.get('original_price', row['price'])) else 0.0,
                    'image_url': str(row.get('image_url', ''))
                }
                
                # 創建商品節點和基本關係
                product_id = session.execute_write(create_product_node, product_data)
                
                # 創建風格關係
                session.execute_write(create_style_relationships, product_id, valid_styles)
                
                imported_rows += 1
                
                # 記錄進度
                if imported_rows % 50 == 0:
                    logger.info(f"Progress: {imported_rows}/{total_rows} products imported ({imported_rows/total_rows*100:.1f}%)")
                
            except Exception as e:
                logger.error(f"Error importing row {idx}: {e}")
                skipped_rows += 1
                continue
    
    logger.info(f"✅ Import completed: {imported_rows} products imported, {skipped_rows} skipped")
    
    # 驗證導入
    verify_import()


def verify_import():
    """驗證資料匯入結果"""
    
    with driver.session() as session:
        # 統計商品數量
        result = session.run("MATCH (p:Product) RETURN count(p) as count")
        product_count = result.single()['count']
        logger.info(f"📊 Total products in database: {product_count}")
        
        # 統計品牌數量
        result = session.run("MATCH (b:Brand) RETURN count(b) as count")
        brand_count = result.single()['count']
        logger.info(f"📊 Total brands: {brand_count}")
        
        # 統計類別數量
        result = session.run("MATCH (c:Category) RETURN count(c) as count")
        category_count = result.single()['count']
        logger.info(f"📊 Total categories: {category_count}")
        
        # 統計風格關係
        result = session.run("MATCH ()-[r:HAS_STYLE]->() RETURN count(r) as count")
        style_rel_count = result.single()['count']
        logger.info(f"📊 Total HAS_STYLE relationships: {style_rel_count}")
        
        # 顯示範例商品
        result = session.run("""
            MATCH (p:Product)-[:HAS_STYLE]->(s:Style)
            MATCH (p)-[:OF_BRAND]->(b:Brand)
            MATCH (p)-[:IN_CATEGORY]->(c:Category)
            WITH p, collect(DISTINCT s.name) as styles, b.name as brand, c.name as category
            RETURN p.name as name, p.price as price, brand, category, styles
            LIMIT 3
        """)
        
        logger.info("\n📦 Sample products:")
        for record in result:
            logger.info(f"  - {record['name']} (${record['price']}) - {record['brand']} | {record['category']} | Styles: {', '.join(record['styles'])}")


def main(products_csv: str, products_csv_with_style: str, 
         nrows: int = None, skip_prediction: bool = False):
    """主函數"""
    
    try:
        # 處理 CSV 文件
        df = process_products(products_csv, products_csv_with_style, nrows, skip_prediction)
        
        # 匯入到 Neo4j
        import_to_neo4j(df)
        
        logger.info("\n🎉 All done! Products successfully loaded into Neo4j")
        
    except Exception as e:
        logger.error(f"❌ Error in main process: {e}")
        raise
    finally:
        close_neo4j()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load product data into Neo4j')
    parser.add_argument('--products_csv', 
                      default="data/queenshop_all_products.csv",
                      help='Path to original products CSV file')
    parser.add_argument('--products_csv_with_style',
                      default="data/queenshop_all_products_with_style.csv",
                      help='Path to output CSV file with predicted styles')
    parser.add_argument('--nrows', type=int, default=None,
                      help='Number of rows to process (optional, for testing)')
    parser.add_argument('--skip_prediction', action='store_true',
                      help='Skip style prediction and use existing processed CSV')
    
    args = parser.parse_args()
    
    main(args.products_csv, args.products_csv_with_style, args.nrows, args.skip_prediction)

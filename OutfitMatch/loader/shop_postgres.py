import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import openai
import psycopg2
import ast
import time
import argparse
import logging
from config.settings import (
    OPENAI_API_KEY,
    POSTGRES_HOST,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

STYLE_LIST = "日系、韓系、歐美、街頭、簡約、運動風、復古、休閒、工裝、優雅、戶外、都會、甜美、性感、正裝、華麗"
PROMPT = """
你是一個時尚穿搭風格專家。根據以下資訊，請判斷這項商品最符合的 1~2 個風格（從下列風格選，最多2個），只回傳 Python list 格式，不需解釋、不需補充。
可選風格有：{style_list}
請用 ['風格1', '風格2'] 或 ['風格1'] 格式回傳，不要有多餘文字。

---
商品名稱：{item}
商品描述：{desc}
---
"""

def predict_style(row):
    prompt = PROMPT.format(
        style_list=STYLE_LIST,
        item=row['name'],
        desc=row['description'],
    )
    for retry in range(3):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error predicting style (attempt {retry + 1}/3): {e}")
            time.sleep(2)
    return "[]"

def process_products(products_csv, products_csv_with_style, nrows=None, skip_prediction=False):
    if skip_prediction and os.path.exists(products_csv_with_style):
        logger.info("Skip prediction mode: Reading existing processed CSV")
        df = pd.read_csv(products_csv_with_style)
    else:
        # Read and process CSV
        logger.info("Reading original CSV and predicting styles")
        df = pd.read_csv(products_csv, nrows=nrows)
        df['predicted_style'] = df.apply(predict_style, axis=1)
        df.to_csv(products_csv_with_style, index=False)
        logger.info("Style prediction completed and saved to CSV")
    
    logger.info(f"DataFrame columns: {df.columns}")
    return df

def setup_database():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS products;")
    conn.commit()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT,
        description TEXT,
        category TEXT,
        brand TEXT,
        price NUMERIC,
        predicted_style TEXT[],
        image_url TEXT
    )
    """)
    conn.commit()
    
    return conn, cur

def import_to_database(df, conn, cur):
    total_rows = len(df)
    imported_rows = 0
    skipped_rows = 0
    
    for idx, row in df.iterrows():
        try:
            # Try to parse the predicted_style string into a list
            try:
                arr = ast.literal_eval(row['predicted_style'])
                if not isinstance(arr, list):
                    raise ValueError("predicted_style must be a list")
            except (ValueError, SyntaxError) as e:
                logger.warning(f"Invalid predicted_style format at row {idx}, using empty list: {e}")
                arr = []
            
            # Insert the row into the database
            cur.execute("""
                INSERT INTO products (name, description, category, brand, price, predicted_style, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                row['name'],
                row['description'],
                row['category'],
                row['brand'],
                row['price'],
                arr,
                row['image_url']
            ))
            imported_rows += 1
            
            # Log progress every 100 rows
            if imported_rows % 100 == 0:
                logger.info(f"Progress: {imported_rows}/{total_rows} rows imported")
                
        except Exception as e:
            logger.error(f"Error importing row {idx}: {e}")
            skipped_rows += 1
            continue

    conn.commit()
    logger.info(f"Import completed: {imported_rows} rows imported, {skipped_rows} rows skipped")
    
    # Verify the import by checking the table structure
    cur.execute("SELECT * FROM products LIMIT 1;")
    logger.info(f"Table columns: {[desc[0] for desc in cur.description]}")

def main(products_csv, products_csv_with_style, nrows, skip_prediction):
    global client
    if not skip_prediction:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Process CSV files
    df = process_products(products_csv, products_csv_with_style, nrows, skip_prediction)
    
    # Setup and import to database
    conn, cur = setup_database()
    try:
        import_to_database(df, conn, cur)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process product data and import to PostgreSQL')
    parser.add_argument('--products_csv', 
                      default="data/queenshop_all_products.csv",
                      help='Path to original products CSV file')
    parser.add_argument('--products_csv_with_style',
                      default="data/queenshop_all_products_with_style.csv",
                      help='Path to output CSV file with predicted styles')
    parser.add_argument('--nrows', type=int, default=None,
                      help='Number of rows to process (optional)')
    parser.add_argument('--skip_prediction', action='store_true',
                      help='Skip style prediction and use existing processed CSV')
    
    args = parser.parse_args()
    main(args.products_csv, args.products_csv_with_style, args.nrows, args.skip_prediction)
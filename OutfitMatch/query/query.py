import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
import psycopg2
import ast
from PIL import Image
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import base64
from io import BytesIO
from config.settings import (
    OPENAI_API_KEY,
    POSTGRES_HOST,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD
)
from loader.instagram_neo4j import (
    segment_and_crop_fashion,
    get_image_embedding,
    fetch_all_post_embeddings_and_info
)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize database connection
conn = None
cur = None

def init_db():
    global conn, cur
    if conn is None:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        cur = conn.cursor()

def close_db():
    global conn, cur
    if cur is not None:
        cur.close()
    if conn is not None:
        conn.close()
        conn = None
        cur = None

def nl_to_sql_where(nl_query):
    prompt_template = """
    你是一個SQL專家。根據下列資料庫結構，把用戶的自然語言問題，轉換成 SQL 的 WHERE 子句（不要SELECT、不要註解），不要加多餘說明，全部寫在同一行，不要用code block或其他markdown格式。
    
    資料庫結構如下：
    products(
        id, name, price, original_price, image_url, description, category, brand, style
    )

    category只分成五個類別：
    - 上衣（T恤、襯衫、風衣、背心、毛衣等屬於穿在上半身的單品）
    - 下身（褲子、短褲、長褲、裙子）
    - 連身（洋裝、連身褲）
    - 配件（包包、帽子、鞋子、襪子）
    - 其他（無法分類的）

    範例：
    「三千元以下的Nike鞋子」 -> brand='Nike' AND price<3000 AND category='配件'
    「Adidas 的運動鞋」 -> brand='Adidas' AND category='配件'
    「2000元以下的上衣」 -> price<2000 AND category='上衣'
    「1000元以下的褲子」 -> price<1000 AND category='下身'
    「500元以下的包包」 -> price<500 AND category='配件'
    「200元以下的帽子」 -> price<200 AND category='配件'
    「100元以下的襪子」 -> price<100 AND category='配件'
    
    問題: {}
    答案:
    """
    full_prompt = prompt_template.format(nl_query)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一個SQL專家"},
            {"role": "user", "content": full_prompt}
        ]
    )
    return resp.choices[0].message.content.strip()

def get_topk_similar_posts(query_img, k=3):
    posts, db_embeddings = fetch_all_post_embeddings_and_info()
    seg_img = segment_and_crop_fashion(query_img)
    query_emb = get_image_embedding(seg_img)
    scores = cosine_similarity(query_emb.reshape(1, -1), db_embeddings)[0]
    top_k_indices = np.argsort(scores)[::-1][:k]
    return [posts[i] for i in top_k_indices], [scores[i] for i in top_k_indices]

def predict_style_for_posts(posts):
    style_results = []
    style_list = "日系、韓系、歐美、街頭、簡約、運動風、復古、休閒、工裝、優雅、戶外、都會、甜美、性感、正裝、華麗"
    prompt_template = """
    你是一個時尚穿搭風格專家。根據以下資訊，請判斷這篇 IG 穿搭貼文最符合的 1~2 個風格（從下列風格選，最多2個），只回傳 Python list 格式，不需解釋、不需補充。
    
    可選風格有：{style_list}
    
    請用 ['風格1', '風格2'] 或 ['風格1'] 格式回傳，不要有多餘文字。
    
    ---
    穿搭描述：{desc}
    商品資訊：{items}
    標籤：{tags}
    ---
    """
    for post in posts:
        desc = post.get('description', '') or ''
        items = post.get('caption', '') or ''
        tags = ''
        prompt = prompt_template.format(style_list=style_list, desc=desc, items=items, tags=tags)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是時尚風格專家"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        style_results.append(response.choices[0].message.content.strip())
    return style_results

def image_to_styles(query_image):
    try:
        print(f"Received image type: {type(query_image)}")
        if isinstance(query_image, str):
            print(f"Image string starts with: {query_image[:100]}...")
            
        # If query_image is a base64 string (check both with and without data:image prefix)
        if isinstance(query_image, str) and (
            query_image.startswith('data:image') or 
            query_image.startswith('/9j/') or  # JPEG
            query_image.startswith('iVBOR')    # PNG
        ):
            print("Processing as base64 image")
            # Remove the data URL prefix if present
            base64_data = query_image.split(',')[1] if ',' in query_image else query_image
            print(f"Base64 data length: {len(base64_data)}")
            # Convert base64 to image
            try:
                img_data = base64.b64decode(base64_data)
                print(f"Decoded image data length: {len(img_data)}")
                img = Image.open(BytesIO(img_data))
                print(f"Successfully opened image: {img.size} {img.mode}")
            except Exception as e:
                print(f"Error decoding base64 image: {e}")
                raise ValueError(f"Invalid base64 image data: {str(e)}")
        # If query_image is already a PIL Image
        elif isinstance(query_image, Image.Image):
            print("Processing as PIL Image")
            img = query_image
            print(f"Image details: {img.size} {img.mode}")
        # If query_image is a file path (should be last condition)
        elif isinstance(query_image, str) and os.path.isfile(query_image):
            print("Processing as file path")
            img = Image.open(query_image)
            print(f"Successfully opened image from file: {img.size} {img.mode}")
        else:
            raise ValueError(f"Invalid image input. Must be a base64 string or PIL Image or file path. Got type {type(query_image)}")

        print("Getting similar posts...")
        top_posts, top_scores = get_topk_similar_posts(img, k=1)
        print("Predicting styles...")
        style_results = predict_style_for_posts(top_posts)
            
        #TODO: 整合多篇貼文預測風格
        result = ast.literal_eval(style_results[0])
        print(f"Predicted styles: {result}")
        return result
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(traceback.format_exc())
        raise

def search_products(sql_where, style_list):
    init_db()  # Ensure database connection is initialized
    sql = f"SELECT id, name, description, category, brand, price, predicted_style, image_url FROM products WHERE ({sql_where}) AND (predicted_style = %s::text[]) LIMIT 10;"
    #print("實際查詢語句：", sql % style_list)
    
    cur.execute(sql, (style_list,))
    products = cur.fetchall()

    if len(products) < 10:
        sql = f"SELECT id, name, description, category, brand, price, predicted_style, image_url FROM products WHERE ({sql_where}) AND (predicted_style && %s::text[]) LIMIT 10;"
        cur.execute(sql, (style_list,))
        products += cur.fetchall()

    if len(products) > 10:
        products = products[:10]
    for prod in products:
        print(prod)
    return products

def user_query(query_text, query_image):
    sql_where = nl_to_sql_where(query_text)
    style_list = image_to_styles(query_image)
    result_products = search_products(sql_where, style_list)
    if len(result_products) > 0:
        return {"text":  f"您上傳的圖片最接近{'、'.join(style_list)}風格，以下是我們的商品列表中符合您的風格與條件的結果：", "products": result_products}
    else:
        return {"text": "您搜尋的內容在我們的商品列表中查不到結果，試試放寬條件吧！", "products": result_products}

if __name__ == "__main__":
    try:
        res = user_query("2000元以下的上衣", "test/images/top.jpg")
        print(res)
        res = user_query("1元以下的上衣", "test/images/top.jpg")
        print(res)
    finally:
        close_db()
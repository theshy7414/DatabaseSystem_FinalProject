import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD
)

# i.連接IG
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
from datetime import datetime
from neo4j import GraphDatabase
import re
from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation, AutoImageProcessor, AutoModel
from PIL import Image
import requests
import torch.nn as nn
import numpy as np
import torch
from sklearn.metrics.pairwise import cosine_similarity
from torchvision import transforms

# Initialize Neo4j connection
driver_neo4j = None

# Initialize ML models
seg_processor = None
seg_model = None
dino_processor = None
dino_model = None
device = None

def init_neo4j():
    global driver_neo4j
    if driver_neo4j is None:
        driver_neo4j = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        create_vector_index()

def close_neo4j():
    global driver_neo4j
    if driver_neo4j is not None:
        driver_neo4j.close()
        driver_neo4j = None

def init_ml_models():
    global seg_processor, seg_model, dino_processor, dino_model, device
    if seg_processor is None:
        seg_processor = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
        seg_model = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes")
        dino_processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
        dino_model = AutoModel.from_pretrained("facebook/dinov2-base")
        dino_model.eval()

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dino_model = dino_model.to(device)

def create_vector_index():
    with driver_neo4j.session() as session:
        try:
            session.run("""
            CALL db.index.vector.createNodeIndex(
                'fashion_post_index',
                'Post',
                'img_emb',
                768,
                'cosine'
            )
            """)
            print("✅ Vector index created.")
        except Exception as e:
            if "already exists" in str(e):
                print("⚠️ Vector index already exists.")
            else:
                print("❌ Failed to create vector index:", e)

seg_processor = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
seg_model = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes")
dino_processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
dino_model = AutoModel.from_pretrained("facebook/dinov2-base")
dino_model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
dino_model = dino_model.to(device)

# Segmentation
def crop_with_mask(image: Image.Image, mask: np.ndarray, bg_color=(255, 255, 255)) -> Image.Image:
    image_np = np.array(image)

    if mask.shape != image_np.shape[:2]:
        raise ValueError("Mask size does not match image size.")

    mask_3d = np.expand_dims(mask, axis=2)
    bg_array = np.full_like(image_np, bg_color)
    result = np.where(mask_3d, image_np, bg_array)

    return Image.fromarray(result)

def get_mask_bbox(mask: np.ndarray):
    ys, xs = np.where(mask == 1)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    return x_min, y_min, x_max, y_max

def crop_fashion_region(image: Image.Image, mask: np.ndarray):
    bbox = get_mask_bbox(mask)
    if not bbox:
        return None
    x1, y1, x2, y2 = bbox
    return image.crop((x1, y1, x2 + 1, y2 + 1)), mask[y1:y2+1, x1:x2+1]

def segment_and_crop_fashion(image: Image.Image, bg_color = (255, 255, 255)):
    inputs = seg_processor(images=image, return_tensors="pt")
    outputs = seg_model(**inputs)
    logits = outputs.logits.cpu()

    upsampled_logits = nn.functional.interpolate(
        logits,
        size=image.size[::-1],
        mode="bilinear",
        align_corners=False,
    )
    pred_seg = upsampled_logits.argmax(dim=1)[0]
    pred_seg_np = pred_seg.numpy()
    fashion_labels = [4, 5, 6, 7, 8, 16, 17]
    fashion_mask = np.isin(pred_seg_np, fashion_labels).astype(np.uint8)
    patch, mask_patch = crop_fashion_region(image, fashion_mask)
    return crop_with_mask(patch, mask_patch, bg_color)

# Embedding
def get_image_embedding(image: Image.Image):
    inputs = dino_processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = dino_model(**inputs)
        embedding = outputs.last_hidden_state[:, 0].cpu().numpy()  # CLS token
    return embedding.squeeze()

# Parse caption
def parse_caption(caption_text):
    item_pattern = r"(Top|Pants|Skirt|Shoes|Cap|Jacket|Coat|Sneakers|Shoe|Hat|Belt|Bag|Outer|Accessories)[：:]\s*([\w\-\d@\. ]+)"
    items = re.findall(item_pattern, caption_text, flags=re.IGNORECASE)

    parts = caption_text.strip().split("\n\n")
    description = parts[1].strip() if len(parts) > 1 else ""

    hashtags = re.findall(r"#\w+", caption_text)

    return items, description, hashtags

# 
def get_full_image_url(soup):
    max_width = 0
    max_url = ""

    # 找到第一個 img（或加入 class 過濾：class_="x5yr21d"）
    img_tag = soup.find("img")
    if img_tag and img_tag.has_attr("srcset"):
        srcset = img_tag["srcset"].split(",")
        for item in srcset:
            parts = item.strip().split(" ")
            if len(parts) == 2:
                url, width = parts
                width_val = int(width.replace("w", ""))
                if width_val > max_width:
                    max_width = width_val
                    max_url = url
    elif img_tag and img_tag.has_attr("src"):
        max_url = img_tag["src"]

    return max_url



# Insert data into Neo4j
def insert_post(tx, user_id, user_name, post_id, url, caption, description, timestamp, items, image_url, hashtags, img_embedding):
    tx.run("""
        MERGE (u:User {id: $user_id})
        SET u.name = $user_name

        MERGE (p:Post {id: $post_id})
        SET p.caption = $caption,
            p.url = $url,
            p.description = $description,
            p.image = $image_url,
            p.timestamp = datetime($timestamp),
            p.img_emb = $img_embedding

        MERGE (u)-[:POSTED]->(p)
    """, user_id=user_id, user_name=user_name,
            post_id=post_id, caption=caption, url=url, description=description, 
            image_url=image_url, timestamp=timestamp, img_embedding=img_embedding)

    tx.run("""
        MERGE (p:Post {url: $url})
        SET p.description = $description
    """, url=url, description=description)

    for item_type, brand in items:
        item_name = f"{item_type}:{brand}"
        tx.run("""
            MATCH (p:Post {id: $post_id})
            MERGE (i:Item {name: $item_name, type: $type})
            MERGE (b:Brand {name: $brand})
            MERGE (i)-[:OF_BRAND]->(b)
            MERGE (p)-[:MENTIONS_ITEM]->(i)
        """, post_id=post_id, item_name=item_name, type=item_type, brand=brand)

    # # For "Style" saving --> Before saved, use LLM 
    # for tag in hashtags:
    #     style_name = tag.strip("#")
    #     tx.run("""
    #         MATCH (p:Post {id: $post_id})
    #         MERGE (s:Style {name: $style})
    #         MERGE (p)-[:HAS_STYLE]->(s)
    #     """, post_id=post_id, style=style_name)

# =====================================================

def fetch_all_post_embeddings_and_info():
    query = """
    MATCH (p:Post)
    RETURN p.id AS id, p.caption AS caption, p.description AS description, 
           p.image AS image_url, p.img_emb AS img_emb
    """
    with driver_neo4j.session() as session:
        result = session.run(query)
        posts = []
        embeddings = []
        for record in result:
            post = record.data()
            posts.append(post)
            emb = post.get("img_emb")
            # 處理存成list或string的情況
            if isinstance(emb, str):
                emb = np.array(eval(emb))
            else:
                emb = np.array(emb)
            embeddings.append(emb)
        return posts, np.vstack(embeddings)
    
def scroll_and_get_posts(driver, max_posts=50):
    """
    Scroll through the profile page and collect post links until we reach max_posts
    or there are no more posts to load.
    """
    post_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while len(post_links) < max_posts:
        # Get all post links on current page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/p/' in href:
                full_url = "https://www.instagram.com" + href
                post_links.add(full_url)
                print(f"Found post {len(post_links)}/{max_posts}: {full_url}")
        
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load
        
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print(f"Reached end of page. Total posts found: {len(post_links)}")
            break
        last_height = new_height
        
        # Add a small delay between scrolls to avoid rate limiting
        time.sleep(1)
    
    return list(post_links)[:max_posts]

def run_scraper(max_posts=50):
    init_ml_models()  # Initialize ML models before scraping
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    try:
        # Go to login interface
        print("Logging in to Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)  

        # Write name: username / password
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        username_input.send_keys(INSTAGRAM_USERNAME)
        password_input.send_keys(INSTAGRAM_PASSWORD)
        password_input.submit()
        time.sleep(5)  

        print("Going to target profile...")
        driver.get("https://www.instagram.com/ootd_introducer/")
        time.sleep(3)

        # Get post links with scrolling
        print(f"Collecting up to {max_posts} posts...")
        post_links = scroll_and_get_posts(driver, max_posts)
        print(f"Found {len(post_links)} posts to process")

        # Process each post
        for i, link in enumerate(post_links, 1):
            try:
                print(f"\nProcessing post {i}/{len(post_links)}: {link}")
                driver.get(link)
                time.sleep(2)  # Increased wait time for post loading

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # For posts' caption
                caption_tag = soup.find("meta", property="og:description")
                caption = caption_tag["content"] if caption_tag else ""

                # For posts' image
                image_url = get_full_image_url(soup)
                if not image_url:
                    print(f"Could not find image URL for post {link}, skipping...")
                    continue
                
                try:
                    # Embedding
                    image = Image.open(requests.get(image_url, stream=True).raw)
                    seg_img = segment_and_crop_fashion(image)
                    img_embedding = get_image_embedding(seg_img)
                except Exception as e:
                    print(f"Error processing image for post {link}: {e}")
                    continue
                
                timestamp = datetime.now().isoformat() 

                if caption:
                    # Semantic
                    items, description, hashtags = parse_caption(caption)
                    print(f"Found {len(items)} items in caption")
                    print(f"Description length: {len(description)}")
                    print(f"Found {len(hashtags)} hashtags")

                # Define ig creator
                user_name = "ootd_introducer"
                user_id = user_name
                post_id = link.rstrip("/").split("/")[-1]

                if caption:
                    items, description, hashtags = parse_caption(caption)

                    # Save to Neo4j
                    with driver_neo4j.session() as session:
                        session.execute_write(
                            insert_post,
                            user_id=user_id,
                            user_name=user_name,
                            post_id=post_id,
                            url=link,
                            caption=caption,
                            description=description,
                            timestamp=timestamp,
                            items=items,
                            image_url=image_url,
                            hashtags=hashtags,
                            img_embedding=img_embedding
                        )

                    print(f"Saved post to Neo4j: {post_id}")
                
                # Add delay between posts to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing post {link}: {e}")
                continue

    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

# Initialize Neo4j connection when imported
init_neo4j()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Scrape Instagram posts')
    parser.add_argument('--max_posts', type=int, default=50,
                      help='Maximum number of posts to scrape (default: 50)')
    args = parser.parse_args()
    
    try:
        run_scraper(max_posts=args.max_posts)
    finally:
        close_neo4j()
"""
Neo4j Database Schema Initialization
創建所有必要的節點標籤、關係類型、約束和索引
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jSchemaInitializer:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    def create_constraints(self):
        """創建唯一性約束確保資料完整性"""
        constraints = [
            # 用戶
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            
            # 貼文
            "CREATE CONSTRAINT post_id IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
            
            # 商品
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            
            # 風格
            "CREATE CONSTRAINT style_name IF NOT EXISTS FOR (s:Style) REQUIRE s.name IS UNIQUE",
            
            # 品牌
            "CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE",
            
            # 類別
            "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
            
            # 單品
            "CREATE CONSTRAINT item_name IF NOT EXISTS FOR (i:Item) REQUIRE i.name IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"✅ Created constraint: {constraint.split('FOR')[1].split('REQUIRE')[0].strip()}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                        logger.info(f"⚠️  Constraint already exists")
                    else:
                        logger.error(f"❌ Error creating constraint: {e}")
    
    def create_indexes(self):
        """創建性能索引"""
        indexes = [
            # 商品相關索引
            "CREATE INDEX product_price IF NOT EXISTS FOR (p:Product) ON (p.price)",
            "CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name)",
            
            # 貼文相關索引
            "CREATE INDEX post_timestamp IF NOT EXISTS FOR (p:Post) ON (p.timestamp)",
            
            # 全文搜索索引
            "CREATE FULLTEXT INDEX product_search IF NOT EXISTS FOR (p:Product) ON EACH [p.name, p.description]",
            "CREATE FULLTEXT INDEX post_search IF NOT EXISTS FOR (p:Post) ON EACH [p.caption, p.description]",
        ]
        
        with self.driver.session() as session:
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"✅ Created index: {index.split('FOR')[1].split('ON')[0].strip()}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                        logger.info(f"⚠️  Index already exists")
                    else:
                        logger.error(f"❌ Error creating index: {e}")
    
    def create_vector_indexes(self):
        """創建向量索引用於圖片相似度搜尋"""
        vector_indexes = [
            {
                "name": "post_image_index",
                "label": "Post",
                "property": "img_embedding",
                "dimensions": 768,
                "similarity": "cosine"
            },
            {
                "name": "product_image_index",
                "label": "Product",
                "property": "img_embedding",
                "dimensions": 768,
                "similarity": "cosine"
            }
        ]
        
        with self.driver.session() as session:
            for idx in vector_indexes:
                try:
                    # Check if index exists
                    result = session.run("SHOW INDEXES YIELD name WHERE name = $name", name=idx['name'])
                    if result.single():
                        logger.info(f"⚠️  Vector index already exists: {idx['name']}")
                        continue
                    
                    # Create vector index
                    query = f"""
                    CREATE VECTOR INDEX {idx['name']} IF NOT EXISTS
                    FOR (n:{idx['label']})
                    ON n.{idx['property']}
                    OPTIONS {{
                        indexConfig: {{
                            `vector.dimensions`: {idx['dimensions']},
                            `vector.similarity_function`: '{idx['similarity']}'
                        }}
                    }}
                    """
                    session.run(query)
                    logger.info(f"✅ Created vector index: {idx['name']} on {idx['label']}.{idx['property']}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"⚠️  Vector index already exists: {idx['name']}")
                    else:
                        logger.error(f"❌ Error creating vector index {idx['name']}: {e}")
    
    def initialize_base_data(self):
        """初始化基礎資料：風格和類別"""
        with self.driver.session() as session:
            # 風格節點
            styles = [
                {"name": "日系", "description": "清新自然、簡約舒適的日本風格"},
                {"name": "韓系", "description": "時尚甜美、注重細節的韓國風格"},
                {"name": "歐美", "description": "大膽前衛、個性鮮明的歐美風格"},
                {"name": "街頭", "description": "休閒率性、潮流時尚的街頭風格"},
                {"name": "簡約", "description": "極簡主義、俐落大方的風格"},
                {"name": "運動風", "description": "運動休閒、活力動感的風格"},
                {"name": "復古", "description": "懷舊經典、vintage 風格"},
                {"name": "休閒", "description": "輕鬆舒適、日常百搭的風格"},
                {"name": "工裝", "description": "實用耐穿、軍事工裝風格"},
                {"name": "優雅", "description": "精緻優雅、知性氣質的風格"},
                {"name": "戶外", "description": "機能性強、戶外休閒風格"},
                {"name": "都會", "description": "都市時尚、現代感強的風格"},
                {"name": "甜美", "description": "可愛甜美、少女感的風格"},
                {"name": "性感", "description": "性感魅力、展現身材的風格"},
                {"name": "正裝", "description": "正式商務、專業得體的風格"},
                {"name": "華麗", "description": "奢華精緻、重視裝飾的風格"},
            ]
            
            for style in styles:
                session.run("""
                    MERGE (s:Style {name: $name})
                    SET s.description = $description
                """, **style)
            logger.info(f"✅ Initialized {len(styles)} style nodes")
            
            # 類別節點
            categories = [
                {"name": "上衣", "description": "T恤、襯衫、風衣、背心、毛衣等上半身單品"},
                {"name": "下身", "description": "褲子、短褲、長褲、裙子等下半身單品"},
                {"name": "連身", "description": "洋裝、連身褲等連身單品"},
                {"name": "配件", "description": "包包、帽子、鞋子、襪子等配件"},
                {"name": "其他", "description": "無法分類的其他商品"},
            ]
            
            for category in categories:
                session.run("""
                    MERGE (c:Category {name: $name})
                    SET c.description = $description
                """, **category)
            logger.info(f"✅ Initialized {len(categories)} category nodes")
    
    def verify_setup(self):
        """驗證設置"""
        with self.driver.session() as session:
            # 檢查約束
            constraints_result = session.run("SHOW CONSTRAINTS")
            constraints_count = len(list(constraints_result))
            logger.info(f"📊 Total constraints: {constraints_count}")
            
            # 檢查索引
            indexes_result = session.run("SHOW INDEXES")
            indexes_count = len(list(indexes_result))
            logger.info(f"📊 Total indexes: {indexes_count}")
            
            # 檢查節點數
            style_count = session.run("MATCH (s:Style) RETURN count(s) as count").single()['count']
            category_count = session.run("MATCH (c:Category) RETURN count(c) as count").single()['count']
            logger.info(f"📊 Styles: {style_count}, Categories: {category_count}")
    
    def run_full_initialization(self):
        """執行完整初始化"""
        logger.info("🚀 Starting Neo4j schema initialization...")
        
        try:
            logger.info("\n1️⃣ Creating constraints...")
            self.create_constraints()
            
            logger.info("\n2️⃣ Creating indexes...")
            self.create_indexes()
            
            logger.info("\n3️⃣ Creating vector indexes...")
            self.create_vector_indexes()
            
            logger.info("\n4️⃣ Initializing base data...")
            self.initialize_base_data()
            
            logger.info("\n5️⃣ Verifying setup...")
            self.verify_setup()
            
            logger.info("\n✅ Neo4j schema initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"\n❌ Error during initialization: {e}")
            raise
        finally:
            self.close()


def main():
    initializer = Neo4jSchemaInitializer()
    initializer.run_full_initialization()


if __name__ == "__main__":
    main()

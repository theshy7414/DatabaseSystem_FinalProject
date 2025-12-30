"""
Build Product Recommendation Relationships
自動分析並建立商品之間的推薦關係
基於風格相似度、類別互補性建立 GOES_WITH 關係
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecommendationBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    def build_style_based_recommendations(self, min_common_styles: int = 1):
        """
        建立基於風格的商品推薦關係
        條件：
        1. 有共同風格
        2. 屬於不同類別（可以互相搭配）
        3. 價格差距不要太大
        """
        with self.driver.session() as session:
            query = """
            MATCH (p1:Product)-[:HAS_STYLE]->(s:Style)<-[:HAS_STYLE]-(p2:Product)
            MATCH (p1)-[:IN_CATEGORY]->(c1:Category)
            MATCH (p2)-[:IN_CATEGORY]->(c2:Category)
            
            WHERE p1.id < p2.id  // 避免重複配對
              AND c1.name <> c2.name  // 不同類別
              AND abs(p1.price - p2.price) < 5000  // 價格差距在 5000 內
            
            WITH p1, p2, 
                 collect(DISTINCT s.name) as common_styles,
                 count(DISTINCT s) as style_match_count
            
            WHERE style_match_count >= $min_common_styles
            
            // 創建雙向推薦關係
            MERGE (p1)-[r1:GOES_WITH]->(p2)
            SET r1.style_match = toFloat(style_match_count),
                r1.common_styles = common_styles,
                r1.score = toFloat(style_match_count) / 
                          (abs(p1.price - p2.price) / 1000.0 + 1.0),
                r1.created_at = datetime()
            
            MERGE (p2)-[r2:GOES_WITH]->(p1)
            SET r2.style_match = toFloat(style_match_count),
                r2.common_styles = common_styles,
                r2.score = toFloat(style_match_count) / 
                          (abs(p1.price - p2.price) / 1000.0 + 1.0),
                r2.created_at = datetime()
            
            RETURN count(DISTINCT r1) as relationships_created
            """
            
            result = session.run(query, min_common_styles=min_common_styles)
            count = result.single()['relationships_created']
            logger.info(f"✅ Created {count} GOES_WITH relationships based on style similarity")
            return count
    
    def build_complete_outfit_recommendations(self):
        """
        建立完整穿搭推薦（上衣 + 下身 + 配件）
        找出常見的風格組合，建立更強的推薦關係
        """
        with self.driver.session() as session:
            # 找上衣 + 下身的組合
            query = """
            MATCH (top:Product)-[:IN_CATEGORY]->(c1:Category {name: '上衣'})
            MATCH (bottom:Product)-[:IN_CATEGORY]->(c2:Category {name: '下身'})
            MATCH (top)-[:HAS_STYLE]->(s:Style)<-[:HAS_STYLE]-(bottom)
            
            WHERE abs(top.price - bottom.price) < 3000
            
            WITH top, bottom, collect(DISTINCT s.name) as styles
            WHERE size(styles) >= 1
            
            MERGE (top)-[r:GOES_WITH]->(bottom)
            SET r.outfit_type = 'top_bottom',
                r.common_styles = styles,
                r.score = toFloat(size(styles)) * 1.5  // 上下身搭配給更高分數
            
            RETURN count(r) as relationships_created
            """
            
            result = session.run(query)
            count = result.single()['relationships_created']
            logger.info(f"✅ Created {count} top-bottom outfit relationships")
            return count
    
    def build_post_inspired_relationships(self):
        """
        建立「貼文啟發」關係
        將相似風格的貼文與商品關聯起來
        """
        with self.driver.session() as session:
            query = """
            MATCH (post:Post)-[:HAS_STYLE]->(s:Style)<-[:HAS_STYLE]-(product:Product)
            
            WITH post, product, 
                 collect(DISTINCT s.name) as common_styles,
                 count(DISTINCT s) as style_count
            
            WHERE style_count >= 1
            
            MERGE (product)-[r:INSPIRED_BY]->(post)
            SET r.common_styles = common_styles,
                r.similarity = toFloat(style_count) / 3.0,  // 假設最多 3 個共同風格
                r.created_at = datetime()
            
            RETURN count(r) as relationships_created
            """
            
            result = session.run(query)
            count = result.single()['relationships_created']
            logger.info(f"✅ Created {count} INSPIRED_BY relationships (Post → Product)")
            return count
    
    def create_style_similarity_graph(self):
        """
        創建風格之間的相似度關係
        基於共同出現在同一商品/貼文中的頻率
        """
        with self.driver.session() as session:
            query = """
            MATCH (s1:Style)<-[:HAS_STYLE]-(n)-[:HAS_STYLE]->(s2:Style)
            WHERE s1.name < s2.name
            
            WITH s1, s2, count(n) as co_occurrence
            WHERE co_occurrence >= 5  // 至少共同出現 5 次
            
            MERGE (s1)-[r:SIMILAR_TO]->(s2)
            SET r.similarity = toFloat(co_occurrence) / 100.0,
                r.co_occurrence = co_occurrence
            
            MERGE (s2)-[r2:SIMILAR_TO]->(s1)
            SET r2.similarity = toFloat(co_occurrence) / 100.0,
                r2.co_occurrence = co_occurrence
            
            RETURN count(DISTINCT r) as relationships_created
            """
            
            result = session.run(query)
            count = result.single()['relationships_created']
            logger.info(f"✅ Created {count} SIMILAR_TO relationships between styles")
            return count
    
    def analyze_and_report(self):
        """分析並報告推薦網路的狀態"""
        with self.driver.session() as session:
            # 統計各類關係
            stats = {}
            
            # GOES_WITH
            result = session.run("MATCH ()-[r:GOES_WITH]->() RETURN count(r) as count")
            stats['GOES_WITH'] = result.single()['count']
            
            # INSPIRED_BY
            result = session.run("MATCH ()-[r:INSPIRED_BY]->() RETURN count(r) as count")
            stats['INSPIRED_BY'] = result.single()['count']
            
            # SIMILAR_TO
            result = session.run("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count")
            stats['SIMILAR_TO'] = result.single()['count']
            
            logger.info("\n📊 Recommendation Network Statistics:")
            logger.info(f"  - Product matching relationships (GOES_WITH): {stats['GOES_WITH']}")
            logger.info(f"  - Post inspiration relationships (INSPIRED_BY): {stats['INSPIRED_BY']}")
            logger.info(f"  - Style similarity relationships (SIMILAR_TO): {stats['SIMILAR_TO']}")
            
            # 找出推薦最多的商品
            result = session.run("""
                MATCH (p:Product)-[r:GOES_WITH]->()
                WITH p, count(r) as recommendation_count
                ORDER BY recommendation_count DESC
                LIMIT 5
                RETURN p.name as name, recommendation_count
            """)
            
            logger.info("\n🏆 Top 5 products with most recommendations:")
            for record in result:
                logger.info(f"  - {record['name']}: {record['recommendation_count']} matches")
            
            # 檢查孤立的商品（沒有推薦關係）
            result = session.run("""
                MATCH (p:Product)
                WHERE NOT (p)-[:GOES_WITH]->()
                RETURN count(p) as isolated_count
            """)
            isolated = result.single()['isolated_count']
            
            if isolated > 0:
                logger.warning(f"\n⚠️  Warning: {isolated} products have no recommendations")
                logger.info("Consider relaxing matching criteria or adding more diverse styles")
    
    def run_full_build(self):
        """執行完整的推薦關係建立流程"""
        logger.info("🚀 Starting recommendation relationship building...\n")
        
        try:
            logger.info("1️⃣ Building style-based product recommendations...")
            self.build_style_based_recommendations(min_common_styles=1)
            
            logger.info("\n2️⃣ Building complete outfit recommendations (top + bottom)...")
            self.build_complete_outfit_recommendations()
            
            logger.info("\n3️⃣ Building post-inspired relationships...")
            self.build_post_inspired_relationships()
            
            logger.info("\n4️⃣ Creating style similarity graph...")
            self.create_style_similarity_graph()
            
            logger.info("\n5️⃣ Analyzing recommendation network...")
            self.analyze_and_report()
            
            logger.info("\n✅ Recommendation relationship building completed!")
            
        except Exception as e:
            logger.error(f"\n❌ Error during build: {e}")
            raise
        finally:
            self.close()


def main():
    builder = RecommendationBuilder()
    builder.run_full_build()


if __name__ == "__main__":
    main()

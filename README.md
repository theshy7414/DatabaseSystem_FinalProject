## OutfitMatch

在OutfitMatch底下創建一個.env檔，填入以下欄位([]是要填的東西，但不加[])：
```
# Instagram Credentials
INSTAGRAM_USERNAME=[IG帳號]
INSTAGRAM_PASSWORD=[IG密碼]

# Neo4j Configuration
NEO4J_URI=bolt://localhost:[neo4j的port]
NEO4J_USER=[neo4j帳號]
NEO4J_PASSWORD=[neo4j密碼]

# OpenAI Configuration
OPENAI_API_KEY=[API_KEY]

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=[postgres的port(但好像目前沒用到)]
POSTGRES_DB=[postgres的DB名稱]
POSTGRES_USER=[postgres帳號]
POSTGRES_PASSWORD=[postgres密碼]
```

用虛擬環境跑`pip install -r requirements.txt`，或缺什麼就安裝什麼

- `python server.py`: 跑server
- `python loader/instagram_neo4j.py`: 抓50篇IG貼文 
- `python loader/shop_postgres.py`: 把csv檔用LLM推論風格，再存到postgres
- - `--products_csv [csv檔]`: 原檔案名稱，不包含風格，預設`data/queenshop_all_products.csv`
- - `--products_csv_with_style [csv檔]`: 加入風格欄位後儲存的檔案名稱，預設`data/queenshop_all_products_with_style.csv`
- - `--nrows [行數]`: LLM推論風格的行數，不加的話就會全跑
- - `--skip_prediction`: 加了這個就會直接用已加入風格欄位的CSV資料存到DB
- `python query/query.py`: 跑兩筆測試的query(文字加圖片找商品)

## ui

`npm install` -> `npm run dev` -> 打開http://localhost:5173/
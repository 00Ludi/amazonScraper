import sqlite3
import datetime
import os

dbPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amazonData.db")
conn = sqlite3.connect(dbPath)
cursor = conn.cursor()

def createTables():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            productUrl TEXT PRIMARY KEY,
            productName TEXT,
            currentPrice REAL,
            lowestPrice REAL,
            highestPrice REAL,
            imageUrl TEXT,
            lastUpdated TEXT
        )
    ''')
    
    conn.commit()
    print("[INFO] Database (amazonData.db) and tables created successfully!")

def saveProduct(productName, currentPrice, productUrl, imageUrl):
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("SELECT currentPrice, lowestPrice, highestPrice FROM products WHERE productUrl=?", (productUrl,))
    result = cursor.fetchone()
    
    if result:
        dbCurrent, dbLowest, dbHighest = result
        newLowest = min(currentPrice, dbLowest)
        newHighest = max(currentPrice, dbHighest)

        cursor.execute('''
            UPDATE products 
            SET productName=?, currentPrice=?, lowestPrice=?, highestPrice=?, imageUrl=?, lastUpdated=?
            WHERE productUrl=?
        ''', (productName, currentPrice, newLowest, newHighest, imageUrl, today, productUrl))
    else:
        cursor.execute('''
            INSERT INTO products (productUrl, productName, currentPrice, lowestPrice, highestPrice, imageUrl, lastUpdated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (productUrl, productName, currentPrice, currentPrice, currentPrice, imageUrl, today))
        
    conn.commit()

# Automatically create tables when this file is imported
createTables()
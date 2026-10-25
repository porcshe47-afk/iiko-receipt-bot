import asyncio
import os
from dotenv import load_dotenv
from src.services.iiko import IikoClient

load_dotenv("/Users/aleksandrbalandin/iiko-receipt-bot/.env")

async def main():
    server_url = os.getenv("IIKO_SERVER_URL", "https://mister-kruassan.iiko.it/resto")
    login = os.getenv("IIKO_LOGIN", "Shef")
    password = os.getenv("IIKO_PASSWORD", "1111")
    
    print(f"🔍 Проверка iiko Server: {server_url} с логином: {login}")

    client = IikoClient(server_url=server_url, login=login, password=password)
    
    try:
        print("\n1️⃣ Получение токена...")
        token = await client.get_token()
        print(f"✅ Успешно! Токен сессии: {token}")
        
        print("\n2️⃣ Получение товаров (номенклатуры)...")
        products = await client.get_nomenclature()
        print(f"✅ Найдено товаров: {len(products)}")
        if products:
            print(f"   Пример товара: {products[0].get('name', products[0])}")
            
        print("\n3️⃣ Получение поставщиков...")
        suppliers = await client.get_suppliers()
        print(f"✅ Найдено поставщиков: {len(suppliers)}")
        if suppliers:
            print(f"   Пример поставщика: {suppliers[0].get('name', suppliers[0])}")
            
        print("\n4️⃣ Получение складов...")
        stores = await client.get_stores()
        print(f"✅ Найдено складов: {len(stores)}")
        if stores:
            print(f"   Пример склада: {stores[0].get('name', stores[0])}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке iiko Server: {e}")

if __name__ == "__main__":
    asyncio.run(main())

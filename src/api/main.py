from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..config import settings
from ..services.iiko import IikoClient
from ..services.gemini import GeminiService
from .auth import get_current_user
import os
import shutil

app = FastAPI(title="iiko Receipt Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

iiko_client = IikoClient(
    server_url=settings.IIKO_SERVER_URL,
    login=settings.IIKO_LOGIN,
    password=settings.IIKO_PASSWORD
)

gemini = GeminiService(api_key=settings.GEMINI_API_KEY)

# Простейшее хранилище сессий в памяти для прототипа
sessions_db: Dict[int, Any] = {}
session_counter = 100

# Монтируем статику
os.makedirs("src/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/webapp")

@app.get("/webapp", response_class=HTMLResponse)
async def webapp_page():
    html_path = "src/static/index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>WebApp interface not found</h1>"

class InvoiceItem(BaseModel):
    name: str
    quantity: float
    unit: str
    price: float
    iiko_product_id: Optional[str] = None

class ConfirmInvoiceRequest(BaseModel):
    session_id: int
    items: List[InvoiceItem]
    store_id: str
    supplier_id: str
    invoice_number: Optional[str] = "1"
    invoice_date: Optional[str] = None

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    global session_counter
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Распознаем через Gemini
        result = await gemini.recognize_invoice(file_path)
        if "error" in result:
            raise HTTPException(status_code=400, detail="Не удалось распознать документ")
            
        session_counter += 1
        sessions_db[session_counter] = result
        
        return {"session_id": session_counter, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@app.get("/api/session/{session_id}")
async def get_session(session_id: int):
    # Получаем распознанные данные из сессии или используем дефолтные для демо
    session_data = sessions_db.get(session_id)
    if session_data and "items" in session_data:
        raw_items = session_data["items"]
    else:
        # Дефолтные тестовые данные, если сессия не найдена
        raw_items = [
            {"name": "Молоко 3.2%", "quantity": 10, "unit": "шт", "price": 85.50},
            {"name": "Хлеб Бородинский", "quantity": 5, "unit": "шт", "price": 45.00}
        ]

    try:
        nomenclature = await iiko_client.get_nomenclature()
        iiko_products = [{"id": p.get("id"), "name": p.get("name")} for p in nomenclature if p.get("id") and p.get("name")]
        
        suppliers = await iiko_client.get_suppliers()
        stores = await iiko_client.get_stores()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch iiko data: {str(e)}")

    results = []
    for item in raw_items:
        match = None
        # Пробуем найти точное или нечеткое совпадение по имени
        for p in iiko_products:
            if item["name"].lower() in p["name"].lower() or p["name"].lower() in item["name"].lower():
                match = {"iiko_id": p["id"], "iiko_name": p["name"], "match_type": "auto"}
                break
        
        results.append({
            "raw": item,
            "suggestion": match
        })

    return {
        "session_id": session_id,
        "items": results,
        "products": iiko_products,
        "suppliers": suppliers,
        "stores": stores
    }

@app.post("/api/confirm")
async def confirm_invoice(req: ConfirmInvoiceRequest):
    try:
        items_xml = ""
        for item in req.items:
            total_sum = round(item.quantity * item.price, 2)
            items_xml += f"""
            <item>
                <productId>{item.iiko_product_id}</productId>
                <amount>{item.quantity}</amount>
                <sum>{total_sum}</sum>
                <price>{item.price}</price>
            </item>"""

        xml_payload = f"""<document>
    <incomingNo>{req.invoice_number}</incomingNo>
    <supplierId>{req.supplier_id}</supplierId>
    <storeId>{req.store_id}</storeId>
    <comment>Разовый закуп из кассы через Telegram Bot</comment>
    <items>{items_xml}</items>
</document>"""

        result = await iiko_client.create_incoming_invoice(xml_payload)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

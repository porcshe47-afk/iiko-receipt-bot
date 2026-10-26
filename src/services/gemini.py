import google.generativeai as genai
from PIL import Image, ImageOps
from pdf2image import convert_from_path
import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def prepare_image_or_pdf(file_path: str):
    """
    Универсальная функция: определяет тип файла, 
    исправляет ориентацию изображений и конвертирует PDF в список картинок.
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    processed_images = []

    if file_extension == '.pdf':
        # Конвертируем страницы PDF в изображения для ИИ
        images = convert_from_path(file_path)
        for img in images:
            # Исправляем ориентацию при необходимости
            img = ImageOps.exif_transpose(img)
            processed_images.append(img)
    else:
        # Открываем картинку и исправляем ориентацию (если фото перевернуто)
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        processed_images.append(img)

    return processed_images

class GeminiService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def recognize_invoice(self, image_path: str) -> Dict[str, Any]:
        processed_images = prepare_image_or_pdf(image_path)
        
        prompt = """
        Распознай накладную (УПД или ТОРГ-12) или кассовый чек на изображении.
        Верни строго JSON объект со следующими полями:
        - date: дата документа (ГГГГ-ММ-ДД)
        - number: номер документа
        - supplier_inn: ИНН поставщика
        - items: список товаров, каждый с полями:
            - name: наименование товара
            - quantity: количество (число)
            - unit: единица измерения
            - price: цена за единицу
            - total: итоговая сумма по строке
            - vat: сумма НДС или процент (если есть)

        Если это кассовый чек, также извлеки информацию из него.
        Если какие-то поля не найдены, поставь null.
        Ответ должен содержать ТОЛЬКО JSON, без markdown разметки.
        """
        
        contents = [prompt] + processed_images
        response = await self.model.generate_content_async(contents)
        
        try:
            # Чистим ответ от возможных markdown блоков ```json ... ```
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
                
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            logger.error(f"Raw response: {response.text}")
            return {"error": "failed_to_parse", "raw": response.text}

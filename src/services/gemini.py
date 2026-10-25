import google.generativeai as genai
import PIL.Image
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def recognize_invoice(self, image_path: str) -> Dict[str, Any]:
        img = PIL.Image.open(image_path)
        
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
        
        response = await self.model.generate_content_async([prompt, img])
        
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

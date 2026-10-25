from typing import List, Dict, Any, Optional, Tuple
from thefuzz import fuzz, process
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.models import ProductMapping

logger = logging.getLogger(__name__)

class MatchingService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_mapping(self, external_name: str, supplier_inn: Optional[str] = None) -> Optional[str]:
        """
        Ищет существующее сопоставление в базе данных.
        """
        query = select(ProductMapping).where(ProductMapping.external_name == external_name)
        if supplier_inn:
            query = query.where(ProductMapping.supplier_inn == supplier_inn)
        
        result = await self.db.execute(query)
        mapping = result.scalars().first()
        return mapping.iiko_product_id if mapping else None

    async def save_mapping(self, external_name: str, iiko_product_id: str, iiko_product_name: str, supplier_inn: Optional[str] = None):
        """
        Сохраняет новое сопоставление.
        """
        mapping = ProductMapping(
            external_name=external_name,
            iiko_product_id=iiko_product_id,
            iiko_product_name=iiko_product_name,
            supplier_inn=supplier_inn
        )
        self.db.add(mapping)
        await self.db.commit()

    def find_best_matches(self, query_name: str, iiko_products: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Использует нечеткий поиск для нахождения наиболее подходящих товаров из iiko.
        iiko_products: список словарей с 'id' и 'name'
        """
        if not iiko_products:
            return []

        # Извлекаем только имена для библиотеки process
        choices = {p['name']: p for p in iiko_products}
        names = list(choices.keys())

        # Находим топ совпадений
        best_matches = process.extract(query_name, names, scorer=fuzz.token_set_ratio, limit=limit)

        results = []
        for name, score in best_matches:
            product = choices[name]
            results.append({
                "iiko_id": product['id'],
                "iiko_name": name,
                "score": score
            })
        
        return results

    async def suggest_product(self, external_name: str, iiko_products: List[Dict[str, Any]], supplier_inn: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Комплексная логика: сначала ищем в БД, если нет - нечеткий поиск.
        """
        # 1. Пробуем найти точное совпадение из истории
        mapped_id = await self.get_mapping(external_name, supplier_inn)
        if mapped_id:
            # Ищем этот ID в текущем списке товаров iiko (чтобы убедиться, что он все еще существует)
            for p in iiko_products:
                if p['id'] == mapped_id:
                    return {"iiko_id": p['id'], "iiko_name": p['name'], "match_type": "history"}

        # 2. Если в истории нет, делаем нечеткий поиск
        matches = self.find_best_matches(external_name, iiko_products, limit=1)
        if matches and matches[0]['score'] > 80: # Порог уверенности 80%
            match = matches[0]
            match["match_type"] = "fuzzy"
            return match

        return None

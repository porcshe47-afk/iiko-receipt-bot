import httpx
import logging
import asyncio
import hashlib
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def xml_to_dict(element) -> Any:
    node = {}
    if element.attrib:
        node.update(element.attrib)
    
    children = list(element)
    if children:
        child_dict = {}
        for child in children:
            parsed_child = xml_to_dict(child)
            if child.tag in child_dict:
                if not isinstance(child_dict[child.tag], list):
                    child_dict[child.tag] = [child_dict[child.tag]]
                child_dict[child.tag].append(parsed_child)
            else:
                child_dict[child.tag] = parsed_child
        node.update(child_dict)
    else:
        if element.text:
            return element.text.strip()
    return node

class IikoClient:
    def __init__(self, server_url: str, login: str, password: str):
        self.server_url = server_url.rstrip("/")
        self.login = login
        self.password = password
        self.token: Optional[str] = None

    async def _make_request(self, method: str, url: str, is_xml_response: bool = False, **kwargs) -> Any:
        max_retries = 3
        retry_delay = 1

        async with httpx.AsyncClient(verify=False) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.request(method, url, **kwargs)
                    if response.status_code == 429:
                        logger.warning(f"Rate limit exceeded (429). Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    
                    response.raise_for_status()
                    text = response.text
                    
                    if is_xml_response or "<" in text[:50]:
                        return text
                    
                    try:
                        return response.json()
                    except Exception:
                        return text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 429 or attempt == max_retries - 1:
                        logger.error(f"HTTP error {e.response.status_code} on {url}: {e.response.text}")
                        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
            raise HTTPException(status_code=429, detail="Too many requests to iiko Server")

    async def get_token(self) -> str:
        if self.token:
            return self.token
        
        url = f"{self.server_url}/api/auth"
        pass_sha1 = hashlib.sha1(self.password.encode('utf-8')).hexdigest()
        
        params = {
            "login": self.login,
            "pass": pass_sha1
        }
        
        result = await self._make_request("GET", url, params=params)
        if isinstance(result, str):
            self.token = result.strip()
        elif isinstance(result, dict) and "token" in result:
            self.token = result["token"]
        else:
            self.token = str(result).strip()
            
        return self.token

    async def _get_params(self) -> Dict[str, Any]:
        token = await self.get_token()
        return {"key": token}

    async def get_nomenclature(self) -> List[Dict[str, Any]]:
        url = f"{self.server_url}/api/v2/entities/products/list"
        params = await self._get_params()
        data = await self._make_request("GET", url, params=params)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("products", data.get("items", []))
        if isinstance(data, str) and "<" in data:
            root = ET.fromstring(data)
            return [xml_to_dict(child) for child in root]
        return []

    async def get_suppliers(self) -> List[Dict[str, Any]]:
        url = f"{self.server_url}/api/suppliers"
        params = await self._get_params()
        xml_text = await self._make_request("GET", url, is_xml_response=True, params=params)
        
        try:
            root = ET.fromstring(xml_text)
            suppliers = []
            for child in root:
                parsed = xml_to_dict(child)
                if isinstance(parsed, dict):
                    suppliers.append(parsed)
            return suppliers
        except Exception as e:
            logger.error(f"Failed to parse suppliers XML: {e}, raw: {xml_text[:200]}...")
            return []

    async def get_stores(self) -> List[Dict[str, Any]]:
        url = f"{self.server_url}/api/corporation/stores"
        params = await self._get_params()
        xml_text = await self._make_request("GET", url, is_xml_response=True, params=params)
        
        try:
            root = ET.fromstring(xml_text)
            stores = []
            for child in root:
                parsed = xml_to_dict(child)
                if isinstance(parsed, dict):
                    stores.append(parsed)
            return stores
        except Exception as e:
            logger.error(f"Failed to parse stores XML: {e}, raw: {xml_text[:200]}...")
            return []

    async def create_incoming_invoice(self, xml_payload: str) -> Any:
        url = f"{self.server_url}/api/documents/import/incomingInvoice"
        params = await self._get_params()
        headers = {"Content-Type": "application/xml"}
        return await self._make_request("POST", url, params=params, headers=headers, data=xml_payload)

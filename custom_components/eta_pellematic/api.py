"""API Client for ETA Heating Systems with Text Value Support."""
import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import aiohttp

LOGGER = logging.getLogger(__name__)

@dataclass
class EtaEndpoint:
    """Represents a discovered leaf endpoint."""
    uri: str
    name: str

class EtaApi:
    """Handling the API communication."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int = 8080):
        self._session = session
        self._base_url = f"http://{host}:{port}"

    async def check_connection(self) -> bool:
        """Verify connection."""
        try:
            async with self._session.get(f"{self._base_url}/user/menu", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def _strip_ns(self, root):
        """Helper to remove XML namespaces."""
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
        return root

    async def discover_endpoints(self) -> Dict[str, EtaEndpoint]:
        """Crawl the ETA XML tree and filter for real sensors."""
        endpoints = {}

        async def fetch_and_crawl(uri: str, path_names: List[str]):
            url = f"{self._base_url}/user/menu{uri}"
            try:
                async with self._session.get(url, timeout=15) as response:
                    if response.status != 200: return
                    root = self._strip_ns(ET.fromstring(await response.text()))
                    
                    menu_node = root.find(".//menu") if root.tag == "eta" else root
                    if menu_node is None: menu_node = root
                    
                    await self._crawl_recursive(menu_node, path_names, endpoints)
            except Exception as e:
                LOGGER.debug("Discovery error at %s: %s", uri, e)

        await fetch_and_crawl("", [])
        return endpoints

    async def _crawl_recursive(self, node: ET.Element, path_names: List[str], endpoints: Dict[str, EtaEndpoint]):
        for child in node:
            if child.tag in ['fub', 'object']:
                name = child.get('name')
                uri = child.get('uri')
                if not name or not uri: continue

                new_path = path_names + [name]
                
                # SMART FILTER: Nur Endknoten (Blätter) als Sensor speichern
                if len(child) == 0:
                    clean_name = " ".join(dict.fromkeys(new_path))
                    endpoints[uri] = EtaEndpoint(uri=uri, name=clean_name)
                
                if len(child) > 0:
                    await self._crawl_recursive(child, new_path, endpoints)
                elif child.tag == 'fub':
                    await self._fetch_sub_menu(uri, new_path, endpoints)

    async def _fetch_sub_menu(self, uri: str, path_names: List[str], endpoints: Dict[str, EtaEndpoint]):
        url = f"{self._base_url}/user/menu{uri}"
        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status == 200:
                    root = self._strip_ns(ET.fromstring(await response.text()))
                    await self._crawl_recursive(root, path_names, endpoints)
        except Exception: pass

    async def get_values(self, uris: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch values including strValue for text states."""
        results = {}
        sem = asyncio.Semaphore(10)

        async def fetch_val(uri: str):
            async with sem:
                url = f"{self._base_url}/user/var{uri}"
                try:
                    async with self._session.get(url, timeout=5) as response:
                        if response.status == 200:
                            root = self._strip_ns(ET.fromstring(await response.text()))
                            val_node = root if root.tag == "value" else root.find(".//value")
                            if val_node is not None:
                                results[uri] = {
                                    'raw': val_node.text,
                                    'str_value': val_node.attrib.get('strValue'),
                                    'unit': val_node.attrib.get('unit', ''),
                                    'scale': float(val_node.attrib.get('scaleFactor', 1)),
                                }
                except Exception: pass
        await asyncio.gather(*(fetch_val(u) for u in uris))
        return results

    async def write_value(self, uri: str, value: Any) -> bool:
        """Write value (POST) to ETA."""
        url = f"{self._base_url}/user/var{uri}"
        try:
            async with self._session.post(url, data={'value': str(value)}) as resp:
                return resp.status == 200
        except Exception: return False

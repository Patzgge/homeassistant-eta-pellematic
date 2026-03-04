import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List
import aiohttp

LOGGER = logging.getLogger(__name__)

@dataclass
class EtaEndpoint:
    uri: str
    name: str

class EtaApi:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int = 8080):
        self._session = session
        self._base_url = f"http://{host}:{port}"

    def _strip_ns(self, root):
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
        return root

    async def check_connection(self) -> bool:
        """Check if the ETA boiler is reachable."""
        try:
            url = f"{self._base_url}/user/menu"
            async with self._session.get(url, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    async def discover_endpoints(self) -> Dict[str, EtaEndpoint]:
        endpoints = {}
        async def fetch_and_crawl(uri: str, path_names: List[str]):
            url = f"{self._base_url}/user/menu{uri}"
            try:
                async with self._session.get(url, timeout=15) as response:
                    if response.status != 200: return
                    root = self._strip_ns(ET.fromstring(await response.text()))
                    menu_node = root.find(".//menu") or root
                    await self._crawl_recursive(menu_node, path_names, endpoints)
            except Exception as e: LOGGER.debug("Discovery error: %s", e)
        await fetch_and_crawl("", [])
        return endpoints

    async def _crawl_recursive(self, node: ET.Element, path_names: List[str], endpoints: Dict[str, EtaEndpoint]):
        for child in node:
            tag, uri, name = child.tag, child.get('uri'), child.get('name')
            if not name or not uri: continue
            new_path = path_names + [name]
            if tag == "object" and len(child) == 0:
                if uri.endswith("/12000"): display_name = "Kessel Status"
                else: display_name = " ".join(dict.fromkeys((new_path[-2:] if len(new_path) >= 2 else new_path)))
                endpoints[uri] = EtaEndpoint(uri=uri, name=display_name)
            if len(child) > 0: await self._crawl_recursive(child, new_path, endpoints)
            elif tag == 'fub': await self._fetch_sub_menu(uri, new_path, endpoints)

    async def _fetch_sub_menu(self, uri: str, path_names: List[str], endpoints: Dict[str, EtaEndpoint]):
        try:
            async with self._session.get(f"{self._base_url}/user/menu{uri}", timeout=10) as response:
                if response.status == 200:
                    root = self._strip_ns(ET.fromstring(await response.text()))
                    await self._crawl_recursive(root, path_names, endpoints)
        except Exception: pass

    async def get_values(self, uris: List[str]) -> Dict[str, Dict[str, Any]]:
        results = {}
        sem = asyncio.Semaphore(10)
        async def fetch_val(uri: str):
            async with sem:
                try:
                    async with self._session.get(f"{self._base_url}/user/var{uri}", timeout=5) as response:
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
        try:
            async with self._session.post(f"{self._base_url}/user/var{uri}", data={'value': str(value)}) as resp:
                return resp.status == 200
        except Exception: return False

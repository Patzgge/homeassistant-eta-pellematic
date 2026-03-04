"""API Client for ETA Heating Systems with Auto-Discovery."""
import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

LOGGER = logging.getLogger(__name__)

@dataclass
class EtaEndpoint:
    """Represents a discovered endpoint (sensor/parameter)."""
    uri: str
    name: str

class EtaApi:
    """Handling the API communication and tree traversal."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int = 8080):
        """Initialize the API."""
        self._session = session
        self._base_url = f"http://{host}:{port}"

    async def check_connection(self) -> bool:
        """Verify connection to the API."""
        try:
            async with self._session.get(f"{self._base_url}/user/menu", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    async def discover_endpoints(self) -> Dict[str, EtaEndpoint]:
        """Crawl the ETA XML tree using verified logic."""
        endpoints = {}

        async def fetch_and_crawl(uri: str, path_names: List[str]):
            url = f"{self._base_url}/user/menu{uri}"
            try:
                async with self._session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return
                    text = await response.text()
                    root = ET.fromstring(text)
                    
                    # Namespace-Bereinigung wie im erfolgreichen Test
                    for el in root.iter():
                        if '}' in el.tag:
                            el.tag = el.tag.split('}', 1)[1]

                    # Startpunkt suchen
                    menu_node = root.find(".//menu") if root.tag == "eta" else root
                    if menu_node is None: menu_node = root

                    await self._crawl_recursive(menu_node, path_names, endpoints)
            except Exception as e:
                LOGGER.debug("Discovery error at %s: %s", uri, e)

        await fetch_and_crawl("", [])
        LOGGER.info("Discovery finished. Found %s endpoints.", len(endpoints))
        return endpoints

    async def _crawl_recursive(self, node: ET.Element, path_names: List[str], endpoints: Dict[str, EtaEndpoint]):
        """Recursive crawler logic verified by Mac test."""
        for child in node:
            if child.tag in ['fub', 'object']:
                name = child.get('name')
                uri = child.get('uri')
                
                if name and uri:
                    new_path = path_names + [name]
                    # Namen generieren (Duplikate entfernen)
                    clean_name = " ".join(dict.fromkeys(new_path))
                    endpoints[uri] = EtaEndpoint(uri=uri, name=clean_name)
                    
                    # Tiefer graben
                    if len(child) > 0:
                        await self._crawl_recursive(child, new_path, endpoints)
                    elif child.tag == 'fub':
                        # Falls ein FUB leer ist, rufen wir ihn über das Netzwerk ab
                        await self._fetch_sub_menu(uri, new_path, endpoints)

    async def _fetch_sub_menu(self, uri: str, path_names: List[str], endpoints: Dict[str, EtaEndpoint]):
        """Fetch a sub-menu for empty FUB nodes."""
        url = f"{self._base_url}/user/menu{uri}"
        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    root = ET.fromstring(text)
                    for el in root.iter():
                        if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
                    await self._crawl_recursive(root, path_names, endpoints)
        except Exception:
            pass

    async def get_values(self, uris: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch values for discovered URIs."""
        results = {}
        sem = asyncio.Semaphore(10)

        async def fetch_val(uri: str):
            async with sem:
                url = f"{self._base_url}/user/var{uri}"
                try:
                    async with self._session.get(url, timeout=5) as response:
                        if response.status == 200:
                            text = await response.text()
                            root = ET.fromstring(text)
                            for el in root.iter():
                                if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
                            
                            val_node = root if root.tag == "value" else root.find(".//value")
                            if val_node is not None:
                                results[uri] = {
                                    'raw': val_node.text,
                                    'str_value': val_node.attrib.get('strValue'),
                                    'unit': val_node.attrib.get('unit', ''),
                                    'scale': float(val_node.attrib.get('scaleFactor', 1)),
                                }
                except Exception:
                    pass

        await asyncio.gather(*(fetch_val(u) for u in uris))
        return results

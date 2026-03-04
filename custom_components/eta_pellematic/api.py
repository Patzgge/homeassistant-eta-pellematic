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
    unit: str = ""


class EtaApi:
    """Handling the API communication and tree traversal."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int = 8080):
        """Initialize the API."""
        self._session = session
        self._base_url = f"http://{host}:{port}"
        self._host = host

    async def check_connection(self) -> bool:
        """Verify connection to the API."""
        url = f"{self._base_url}/user/menu"
        try:
            async with self._session.get(url, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    async def discover_endpoints(self) -> Dict[str, EtaEndpoint]:
        """Crawl the ETA XML tree to find all available sensors."""
        endpoints = {}

        # Helper to fetch and parse XML
        async def fetch_xml(uri: str) -> Optional[ET.Element]:
            url = f"{self._base_url}/user/menu{uri}"
            try:
                async with self._session.get(url) as response:
                    if response.status != 200:
                        return None
                    text = await response.text()
                    # ETA sometimes returns invalid XML chars, simpler parse usually works
                    return ET.fromstring(text)
            except Exception as e:
                LOGGER.debug("Failed to fetch menu %s: %s", uri, e)
                return None

        # Recursive crawler
        async def crawl(uri: str, path_names: List[str]):
            root = await fetch_xml(uri)
            if root is None:
                return

            # Process Objects (Leaves/Sensors)
            for obj in root.findall("object"):
                obj_uri = obj.get("uri")
                obj_name = obj.get("name")

                if obj_uri and obj_name:
                    full_path = path_names + [obj_name]
                    clean_name = self._generate_clean_name(full_path)
                    
                    endpoints[obj_uri] = EtaEndpoint(
                        uri=obj_uri,
                        name=clean_name
                    )

            # Process Function Blocks (Folders) -> Recurse
            tasks = []
            for fub in root.findall("fub"):
                fub_uri = fub.get("uri")
                fub_name = fub.get("name")
                if fub_uri:
                    # Append current name to path and recurse
                    new_path = path_names + [fub_name] if fub_name else path_names
                    tasks.append(crawl(fub_uri, new_path))
            
            # Run tasks concurrently
            if tasks:
                await asyncio.gather(*tasks)

        LOGGER.info("Starting ETA Auto-Discovery...")
        await crawl("", [])
        LOGGER.info("Discovery finished. Found %s endpoints.", len(endpoints))
        return endpoints

    def _generate_clean_name(self, path_list: List[str]) -> str:
        """Clean up the name path to avoid duplicates like 'Kessel Kessel'."""
        if not path_list:
            return "Unknown"

        clean_path = []
        for i, part in enumerate(path_list):
            if not part:
                continue
            # Skip duplicates if the previous part is identical
            if i > 0 and part == path_list[i-1]:
                continue
            clean_path.append(part)

        return " ".join(clean_path)

    async def get_values(self, uris: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch values for a list of URIs."""
        results = {}
        # Limit concurrency to avoid overloading the ETA controller
        # 10 concurrent requests is usually safe for ETA PU/PC systems
        sem = asyncio.Semaphore(10)

        async def fetch_single(uri: str):
            async with sem:
                url = f"{self._base_url}/user/var{uri}"
                try:
                    async with self._session.get(url) as response:
                        if response.status == 200:
                            text = await response.text()
                            parsed = self._parse_value_xml(text)
                            if parsed:
                                results[uri] = parsed
                except Exception as e:
                    LOGGER.debug("Error fetching %s: %s", uri, e)

        tasks = [fetch_single(uri) for uri in uris]
        await asyncio.gather(*tasks)
        return results

    def _parse_value_xml(self, xml_string: str) -> Optional[Dict[str, Any]]:
        """Parse the variable XML response."""
        try:
            root = ET.fromstring(xml_string)
            val_node = root if root.tag == 'value' else root.find('.//value')

            if val_node is not None:
                return {
                    'raw': val_node.text,
                    'str_value': val_node.attrib.get('strValue'),
                    'unit': val_node.attrib.get('unit', ''),
                    'scale': float(val_node.attrib.get('scaleFactor', 1)),
                    'dec_places': int(val_node.attrib.get('decPlaces', 0))
                }
            return None
        except ET.ParseError:
            return None

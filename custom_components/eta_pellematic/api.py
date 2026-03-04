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

    def _strip_namespaces(self, xml_string: str) -> ET.Element:
        """Parse XML and strip namespaces to make finding tags easier."""
        # We process the tags to remove {http://...} prefixes
        try:
            # Iterparse is robust, but for small files standard parse + strip is fine
            it = ET.iterparse(asyncio.StreamReader(xml_string) if False else [xml_string]) 
            # Actually, standard fromstring is easier, then walk and strip
            root = ET.fromstring(xml_string)
            
            # Helper to strip namespace from a single tag
            def strip(elem):
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
                for child in elem:
                    strip(child)
            
            strip(root)
            return root
        except Exception:
            # Fallback if stripping fails
            return ET.fromstring(xml_string)

    async def discover_endpoints(self) -> Dict[str, EtaEndpoint]:
        """Crawl the ETA XML tree to find all available sensors."""
        endpoints = {}

        async def fetch_xml(uri: str) -> Optional[ET.Element]:
            url = f"{self._base_url}/user/menu{uri}"
            try:
                async with self._session.get(url) as response:
                    if response.status != 200:
                        return None
                    text = await response.text()
                    # Use our robust namespace stripper
                    return self._strip_namespaces(text)
            except Exception as e:
                LOGGER.debug("Failed to fetch menu %s: %s", uri, e)
                return None

        # Recursive crawler that handles FUBs AND nested Objects
        async def crawl(uri: str, path_names: List[str]):
            root = await fetch_xml(uri)
            if root is None:
                return

            # Find the starting point (Menu) if we are at root
            start_node = root
            if root.tag == 'eta':
                menu_node = root.find('menu')
                if menu_node is not None:
                    start_node = menu_node
            
            # Iterate through children (fub or object)
            tasks = []
            
            for child in start_node:
                child_uri = child.get("uri")
                child_name = child.get("name")
                
                if not child_uri:
                    continue

                # Prepare common data
                new_path = path_names + [child_name] if child_name else path_names
                
                # Check if it is a folder structure (Fub or nested Object)
                # In your XML, Objects can contain Objects. 
                # If an object has children, it's a folder. If not, it's a sensor (usually).
                # But to be safe, we just register EVERYTHING that has a URI as an endpoint,
                # AND recurse down if it looks like a folder.
                
                clean_name = self._generate_clean_name(new_path)
                
                # Register this as an endpoint
                endpoints[child_uri] = EtaEndpoint(
                    uri=child_uri,
                    name=clean_name
                )
                
                # RECURSION LOGIC:
                # If it's a 'fub', we definitely recurse.
                # If it's an 'object' AND has no children in the current XML snippet, 
                # we assume we might need to query it to see if it has children?
                # Actually, ETA menu XML usually lists children if they exist.
                # Your XML shows <object><object>...</object></object>.
                
                if child.tag == 'fub' or (child.tag == 'object' and len(child) > 0):
                    # It has children or is a folder -> Go Deeper
                    # We don't need a network request if the children are already here!
                    # Optimization: If the children are already in 'child', we can recurse locally 
                    # instead of fetching via HTTP again.
                    
                    if len(child) > 0:
                        # Process children locally (recursion without HTTP)
                        await crawl_local(child, new_path)
                    else:
                        # Fetch via HTTP (standard FUB behavior)
                        tasks.append(crawl(child_uri, new_path))

            if tasks:
                await asyncio.gather(*tasks)

        # Local recursive helper to avoid HTTP calls when XML is nested
        async def crawl_local(node: ET.Element, path_names: List[str]):
            for child in node:
                child_uri = child.get("uri")
                child_name = child.get("name")
                if child_uri:
                    new_path = path_names + [child_name] if child_name else path_names
                    clean_name = self._generate_clean_name(new_path)
                    
                    endpoints[child_uri] = EtaEndpoint(uri=child_uri, name=clean_name)
                    
                    if len(child) > 0:
                        await crawl_local(child, new_path)

        LOGGER.info("Starting ETA Auto-Discovery...")
        await crawl("", [])
        LOGGER.info("Discovery finished. Found %s endpoints.", len(endpoints))
        return endpoints

    def _generate_clean_name(self, path_list: List[str]) -> str:
        """Clean up the name path."""
        if not path_list:
            return "Unknown"
        clean_path = []
        for i, part in enumerate(path_list):
            if not part:
                continue
            if i > 0 and part == path_list[i-1]:
                continue
            clean_path.append(part)
        return " ".join(clean_path)

    async def get_values(self, uris: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch values for a list of URIs."""
        results = {}
        sem = asyncio.Semaphore(10)

        async def fetch_single(uri: str):
            async with sem:
                url = f"{self._base_url}/user/var{uri}"
                try:
                    async with self._session.get(url) as response:
                        if response.status == 200:
                            text = await response.text()
                            # Strip namespaces here too!
                            root = self._strip_namespaces(text)
                            parsed = self._parse_value_xml_element(root)
                            if parsed:
                                results[uri] = parsed
                except Exception as e:
                    LOGGER.debug("Error fetching %s: %s", uri, e)

        tasks = [fetch_single(uri) for uri in uris]
        await asyncio.gather(*tasks)
        return results

    def _parse_value_xml_element(self, root: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse from an already processed ElementTree object."""
        try:
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
        except Exception:
            return None

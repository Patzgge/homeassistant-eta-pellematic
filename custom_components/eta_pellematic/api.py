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

        async def fetch_xml(uri: str) -> Optional[ET.Element]:
            url = f"{self._base_url}/user/menu{uri}"
            try:
                async with self._session.get(url) as response:
                    if response.status != 200:
                        return None
                    text = await response.text()
                    return ET.fromstring(text)
            except Exception as e:
                LOGGER.debug("Failed to fetch menu %s: %s", uri, e)
                return None

        async def crawl(uri: str, path_names: List[str]):
            root = await fetch_xml(uri)
            if root is None:
                return

            # Wir nutzen XPath mit Wildcards '{*}', um Namespaces zu ignorieren
            # Das ist die sauberste Methode in Python
            
            # 1. Menü-Knoten finden (falls wir am Root sind)
            menu_node = root
            if "eta" in root.tag:
                found = root.find(".//{*}menu")
                if found is not None:
                    menu_node = found

            # 2. Durch alle Kinder iterieren (fub und object)
            for child in menu_node:
                # Tag-Namen ohne Namespace extrahieren
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                
                child_uri = child.get("uri")
                child_name = child.get("name")
                
                if not child_uri or not child_name:
                    continue

                new_path = path_names + [child_name]
                
                if tag_name == "object":
                    # Es ist ein Sensor -> Speichern
                    clean_name = self._generate_clean_name(new_path)
                    endpoints[child_uri] = EtaEndpoint(uri=child_uri, name=clean_name)
                    
                    # Falls das Objekt Kinder hat, lokal weitergraben
                    if len(child) > 0:
                        crawl_local(child, new_path)
                
                elif tag_name == "fub":
                    # Es ist ein Funktionsblock -> Neue HTTP Anfrage für Untermenü
                    await crawl(child_uri, new_path)

        def crawl_local(node: ET.Element, path_names: List[str]):
            """Durchsucht verschachtelte Objekte im selben XML Dokument."""
            for child in node:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                child_uri = child.get("uri")
                child_name = child.get("name")
                
                if child_uri and child_name and tag_name == "object":
                    new_path = path_names + [child_name]
                    clean_name = self._generate_clean_name(new_path)
                    endpoints[child_uri] = EtaEndpoint(uri=child_uri, name=clean_name)
                    
                    if len(child) > 0:
                        crawl_local(child, new_path)

        LOGGER.info("Starting ETA Auto-Discovery...")
        await crawl("", [])
        LOGGER.info("Discovery finished. Found %s endpoints.", len(endpoints))
        return endpoints

    def _generate_clean_name(self, path_list: List[str]) -> str:
        """Namen säubern."""
        clean_path = []
        for i, part in enumerate(path_list):
            if i > 0 and part == path_list[i-1]:
                continue
            clean_path.append(part)
        return " ".join(clean_path)

    async def get_values(self, uris: List[str]) -> Dict[str, Dict[str, Any]]:
        """Werte abrufen."""
        results = {}
        async with aiohttp.ClientSession() as session: # Sicherer für Einzelabrufe
            for uri in uris:
                url = f"{self._base_url}/user/var{uri}"
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            text = await response.text()
                            root = ET.fromstring(text)
                            # Suche den 'value' Knoten unabhängig vom Namespace
                            val_node = root.find(".//{*}value")
                            if val_node is None and "value" in root.tag:
                                val_node = root
                            
                            if val_node is not None:
                                results[uri] = {
                                    'raw': val_node.text,
                                    'str_value': val_node.attrib.get('strValue'),
                                    'unit': val_node.attrib.get('unit', ''),
                                    'scale': float(val_node.attrib.get('scaleFactor', 1)),
                                    'dec_places': int(val_node.attrib.get('decPlaces', 0))
                                }
                except Exception:
                    continue
        return results

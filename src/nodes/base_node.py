import aiohttp
import asyncio
import logging
from typing import Any, Dict, Optional


class BaseNode:
    def __init__(self, node_id: str, address: str, cluster_nodes: list[str]):
        self.node_id = node_id
        self.address = address
        self.cluster_nodes = cluster_nodes
        self.peer_nodes = [
            node for node in cluster_nodes
            if node != address
        ]
        self.logger = logging.getLogger(node_id)

    async def send_message(
        self,
        target_url: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 3
    ) -> Optional[Dict[str, Any]]:
        url = f"{target_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload or {},
                    timeout=timeout
                ) as response:
                    if response.status >= 400:
                        self.logger.warning(
                            "Request to %s failed with status %s",
                            url,
                            response.status
                        )
                        return None

                    return await response.json()

        except asyncio.TimeoutError:
            self.logger.warning("Timeout when sending message to %s", url)
            return None

        except aiohttp.ClientError as error:
            self.logger.warning("Network error to %s: %s", url, error)
            return None

    async def broadcast(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> list[Optional[Dict[str, Any]]]:
        tasks = [
            self.send_message(peer, endpoint, payload)
            for peer in self.peer_nodes
        ]

        if not tasks:
            return []

        return await asyncio.gather(*tasks, return_exceptions=False)
import json
import time
from collections import OrderedDict
from typing import Any, Dict, List

import aiohttp
import redis.asyncio as redis


class DistributedCacheNode:
    MODIFIED = "M"
    EXCLUSIVE = "E"
    SHARED = "S"
    INVALID = "I"

    def __init__(
        self,
        node_id: str,
        address: str,
        cluster_nodes: List[str],
        redis_client: redis.Redis,
        capacity: int = 3
    ):
        self.node_id = node_id
        self.address = address
        self.cluster_nodes = cluster_nodes
        self.peer_nodes = [
            node for node in cluster_nodes
            if node != address
        ]
        self.redis = redis_client
        self.capacity = capacity

        self.cache = OrderedDict()

        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "writes": 0,
            "invalidations": 0,
            "updates_received": 0,
            "evictions": 0
        }

    def _data_key(self, key: str) -> str:
        return f"cache:data:{key}"

    def _owners_key(self, key: str) -> str:
        return f"cache:owners:{key}"

    def _touch(self, key: str):
        if key in self.cache:
            self.cache.move_to_end(key)

    def _evict_if_needed(self):
        while len(self.cache) > self.capacity:
            evicted_key, _ = self.cache.popitem(last=False)
            self.metrics["evictions"] += 1
            return evicted_key

        return None

    async def _broadcast(self, endpoint: str, payload: Dict[str, Any]):
        async with aiohttp.ClientSession() as session:
            tasks = []

            for peer in self.peer_nodes:
                tasks.append(
                    session.post(
                        f"{peer}{endpoint}",
                        json=payload,
                        timeout=3
                    )
                )

            for task in tasks:
                try:
                    async with task:
                        pass
                except Exception:
                    pass

    async def read(self, key: str) -> Dict[str, Any]:
        if key in self.cache:
            entry = self.cache[key]

            if entry["state"] != self.INVALID:
                self.metrics["cache_hits"] += 1
                self._touch(key)

                return {
                    "success": True,
                    "key": key,
                    "value": entry["value"],
                    "state": entry["state"],
                    "source": "local_cache",
                    "cache_hit": True
                }

        self.metrics["cache_misses"] += 1

        raw_value = await self.redis.get(self._data_key(key))

        if raw_value is None:
            return {
                "success": False,
                "key": key,
                "reason": "key not found in distributed cache store",
                "cache_hit": False
            }

        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode()

        stored = json.loads(raw_value)
        owners = await self.redis.smembers(self._owners_key(key))

        if not owners:
            state = self.EXCLUSIVE
        else:
            state = self.SHARED

        self.cache[key] = {
            "value": stored["value"],
            "state": state,
            "updated_at": stored["updated_at"]
        }

        self._touch(key)
        self._evict_if_needed()

        await self.redis.sadd(self._owners_key(key), self.address)

        return {
            "success": True,
            "key": key,
            "value": stored["value"],
            "state": state,
            "source": "redis_backing_store",
            "cache_hit": False
        }

    async def write(
        self,
        key: str,
        value: Any,
        client_id: str,
        propagation: str = "invalidate"
    ) -> Dict[str, Any]:
        stored = {
            "value": value,
            "updated_at": time.time(),
            "writer": self.node_id,
            "client_id": client_id
        }

        await self.redis.set(
            self._data_key(key),
            json.dumps(stored)
        )

        await self.redis.delete(self._owners_key(key))
        await self.redis.sadd(self._owners_key(key), self.address)

        self.cache[key] = {
            "value": value,
            "state": self.MODIFIED,
            "updated_at": stored["updated_at"]
        }

        self._touch(key)
        evicted_key = self._evict_if_needed()

        self.metrics["writes"] += 1

        if propagation == "update":
            await self._broadcast(
                "/cache/internal/update",
                {
                    "key": key,
                    "value": value,
                    "updated_at": stored["updated_at"],
                    "source_node": self.node_id
                }
            )
        else:
            await self._broadcast(
                "/cache/internal/invalidate",
                {
                    "key": key,
                    "source_node": self.node_id
                }
            )

        return {
            "success": True,
            "key": key,
            "value": value,
            "state": self.MODIFIED,
            "message": "cache written with MESI coherence",
            "propagation": propagation,
            "evicted_key": evicted_key
        }

    async def delete(self, key: str) -> Dict[str, Any]:
        await self.redis.delete(self._data_key(key))
        await self.redis.delete(self._owners_key(key))

        if key in self.cache:
            del self.cache[key]

        await self._broadcast(
            "/cache/internal/invalidate",
            {
                "key": key,
                "source_node": self.node_id
            }
        )

        return {
            "success": True,
            "key": key,
            "message": "key deleted and invalidation broadcasted"
        }

    async def invalidate(self, key: str, source_node: str) -> Dict[str, Any]:
        if key in self.cache:
            self.cache[key]["state"] = self.INVALID
            self.metrics["invalidations"] += 1

        await self.redis.srem(self._owners_key(key), self.address)

        return {
            "success": True,
            "key": key,
            "message": "cache line invalidated",
            "source_node": source_node
        }

    async def update_from_peer(
        self,
        key: str,
        value: Any,
        updated_at: float,
        source_node: str
    ) -> Dict[str, Any]:
        self.cache[key] = {
            "value": value,
            "state": self.SHARED,
            "updated_at": updated_at
        }

        self._touch(key)
        self._evict_if_needed()

        await self.redis.sadd(self._owners_key(key), self.address)

        self.metrics["updates_received"] += 1

        return {
            "success": True,
            "key": key,
            "message": "cache line updated from peer",
            "state": self.SHARED,
            "source_node": source_node
        }

    def status(self) -> Dict[str, Any]:
        clean_cache = {}

        for key, entry in self.cache.items():
            clean_cache[key] = {
                "value": entry["value"],
                "state": entry["state"],
                "updated_at": entry["updated_at"]
            }

        return {
            "node_id": self.node_id,
            "address": self.address,
            "capacity": self.capacity,
            "cache": clean_cache,
            "metrics": self.metrics
        }
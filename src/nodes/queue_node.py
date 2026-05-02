import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

import redis.asyncio as redis


class DistributedQueueNode:
    def __init__(
        self,
        node_id: str,
        address: str,
        cluster_nodes: List[str],
        redis_client: redis.Redis,
        visibility_timeout: int = 30
    ):
        self.node_id = node_id
        self.address = address
        self.cluster_nodes = sorted(cluster_nodes)
        self.redis = redis_client
        self.visibility_timeout = visibility_timeout

    def _hash(self, value: str) -> int:
        return int(hashlib.sha256(value.encode()).hexdigest(), 16)

    def get_queue_owner(self, queue_name: str) -> str:
        queue_hash = self._hash(queue_name)

        ring = sorted(
            (self._hash(node), node)
            for node in self.cluster_nodes
        )

        for node_hash, node in ring:
            if queue_hash <= node_hash:
                return node

        return ring[0][1]

    def is_owner(self, queue_name: str) -> bool:
        return self.get_queue_owner(queue_name) == self.address

    def _ready_key(self, queue_name: str) -> str:
        return f"dqueue:{queue_name}:ready"

    def _processing_key(self, queue_name: str) -> str:
        return f"dqueue:{queue_name}:processing"

    def _metrics_key(self, queue_name: str) -> str:
        return f"dqueue:{queue_name}:metrics"

    async def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        producer_id: str
    ) -> Dict[str, Any]:
        message = {
            "message_id": str(uuid.uuid4()),
            "queue_name": queue_name,
            "payload": payload,
            "producer_id": producer_id,
            "created_at": time.time(),
            "attempts": 0
        }

        await self.redis.rpush(
            self._ready_key(queue_name),
            json.dumps(message)
        )

        await self.redis.hincrby(
            self._metrics_key(queue_name),
            "total_enqueued",
            1
        )

        return {
            "success": True,
            "message": "message enqueued",
            "queue_name": queue_name,
            "message_id": message["message_id"],
            "owner": self.address
        }

    async def dequeue(
        self,
        queue_name: str,
        consumer_id: str
    ) -> Dict[str, Any]:
        raw_message = await self.redis.lpop(self._ready_key(queue_name))

        if raw_message is None:
            return {
                "success": False,
                "reason": "queue is empty",
                "queue_name": queue_name
            }

        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode()

        message = json.loads(raw_message)
        message["consumer_id"] = consumer_id
        message["processing_started_at"] = time.time()
        message["attempts"] = message.get("attempts", 0) + 1

        await self.redis.hset(
            self._processing_key(queue_name),
            message["message_id"],
            json.dumps(message)
        )

        await self.redis.hincrby(
            self._metrics_key(queue_name),
            "total_dequeued",
            1
        )

        return {
            "success": True,
            "message": "message dequeued",
            "queue_name": queue_name,
            "message_id": message["message_id"],
            "payload": message["payload"],
            "attempts": message["attempts"],
            "owner": self.address
        }

    async def ack(
        self,
        queue_name: str,
        message_id: str,
        consumer_id: str
    ) -> Dict[str, Any]:
        raw_message = await self.redis.hget(
            self._processing_key(queue_name),
            message_id
        )

        if raw_message is None:
            return {
                "success": False,
                "reason": "message not found in processing queue",
                "queue_name": queue_name,
                "message_id": message_id
            }

        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode()

        message = json.loads(raw_message)

        if message.get("consumer_id") != consumer_id:
            return {
                "success": False,
                "reason": "consumer_id does not match message owner",
                "queue_name": queue_name,
                "message_id": message_id
            }

        await self.redis.hdel(
            self._processing_key(queue_name),
            message_id
        )

        await self.redis.hincrby(
            self._metrics_key(queue_name),
            "total_acked",
            1
        )

        return {
            "success": True,
            "message": "message acknowledged",
            "queue_name": queue_name,
            "message_id": message_id
        }

    async def recover_expired_messages(
        self,
        queue_name: str
    ) -> Dict[str, Any]:
        processing_key = self._processing_key(queue_name)
        all_processing = await self.redis.hgetall(processing_key)

        now = time.time()
        recovered = []

        for message_id_raw, raw_message in all_processing.items():
            message_id = (
                message_id_raw.decode()
                if isinstance(message_id_raw, bytes)
                else message_id_raw
            )

            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode()

            message = json.loads(raw_message)
            started_at = message.get("processing_started_at", now)

            if now - started_at >= self.visibility_timeout:
                message.pop("consumer_id", None)
                message.pop("processing_started_at", None)

                await self.redis.rpush(
                    self._ready_key(queue_name),
                    json.dumps(message)
                )

                await self.redis.hdel(processing_key, message_id)

                recovered.append(message_id)

        if recovered:
            await self.redis.hincrby(
                self._metrics_key(queue_name),
                "total_recovered",
                len(recovered)
            )

        return {
            "success": True,
            "queue_name": queue_name,
            "recovered_count": len(recovered),
            "recovered_message_ids": recovered
        }

    async def status(self, queue_name: str) -> Dict[str, Any]:
        ready_count = await self.redis.llen(self._ready_key(queue_name))
        processing_count = await self.redis.hlen(self._processing_key(queue_name))
        metrics = await self.redis.hgetall(self._metrics_key(queue_name))

        clean_metrics = {}

        for key, value in metrics.items():
            clean_key = key.decode() if isinstance(key, bytes) else key
            clean_value = value.decode() if isinstance(value, bytes) else value
            clean_metrics[clean_key] = int(clean_value)

        return {
            "queue_name": queue_name,
            "owner": self.get_queue_owner(queue_name),
            "current_node": self.address,
            "is_owner": self.is_owner(queue_name),
            "ready_count": ready_count,
            "processing_count": processing_count,
            "metrics": clean_metrics
        }
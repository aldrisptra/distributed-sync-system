import aiohttp
import redis.asyncio as redis
from aiohttp import web

from src.consensus.raft import RaftNode
from src.nodes.lock_manager import DistributedLockManager
from src.nodes.queue_node import DistributedQueueNode
from src.nodes.cache_node import DistributedCacheNode
from src.utils.config import get_config


async def health_check(request):
    config = request.app["config"]

    return web.json_response({
        "status": "ok",
        "node_id": config.node_id,
        "port": config.node_port,
        "message": "Distributed sync node is running"
    })


async def raft_status(request):
    raft = request.app["raft"]
    return web.json_response(raft.get_status())


async def request_vote(request):
    raft = request.app["raft"]
    data = await request.json()
    result = await raft.handle_request_vote(data)
    return web.json_response(result)


async def append_entries(request):
    raft = request.app["raft"]
    data = await request.json()
    result = await raft.handle_append_entries(data)
    return web.json_response(result)


async def enable_partition(request):
    raft = request.app["raft"]
    raft.partitioned = True

    return web.json_response({
        "status": "ok",
        "message": f"{raft.node_id} is now partitioned"
    })


async def disable_partition(request):
    raft = request.app["raft"]
    raft.partitioned = False

    return web.json_response({
        "status": "ok",
        "message": f"{raft.node_id} partition disabled"
    })


async def acquire_lock(request):
    raft = request.app["raft"]
    lock_manager = request.app["lock_manager"]
    data = await request.json()

    resource = data.get("resource")
    client_id = data.get("client_id")
    lock_type = data.get("lock_type")

    if not resource or not client_id or not lock_type:
        return web.json_response({
            "success": False,
            "reason": "resource, client_id, and lock_type are required"
        }, status=400)

    if raft.state != raft.LEADER:
        return web.json_response({
            "success": False,
            "reason": "this node is not the leader",
            "leader_id": raft.leader_id
        }, status=409)

    preview_result = lock_manager.acquire_lock(resource, client_id, lock_type)

    if not preview_result["success"]:
        return web.json_response(preview_result, status=409)

    lock_manager.release_lock(resource, client_id)

    command = {
        "type": "acquire_lock",
        "resource": resource,
        "client_id": client_id,
        "lock_type": lock_type
    }

    replicated = await raft.replicate_log(command)

    if not replicated:
        return web.json_response({
            "success": False,
            "reason": "failed to replicate lock command to majority"
        }, status=503)

    return web.json_response({
        "success": True,
        "resource": resource,
        "client_id": client_id,
        "lock_type": lock_type,
        "message": "lock acquired and replicated using Raft"
    })


async def release_lock(request):
    raft = request.app["raft"]
    data = await request.json()

    resource = data.get("resource")
    client_id = data.get("client_id")

    if not resource or not client_id:
        return web.json_response({
            "success": False,
            "reason": "resource and client_id are required"
        }, status=400)

    if raft.state != raft.LEADER:
        return web.json_response({
            "success": False,
            "reason": "this node is not the leader",
            "leader_id": raft.leader_id
        }, status=409)

    command = {
        "type": "release_lock",
        "resource": resource,
        "client_id": client_id
    }

    replicated = await raft.replicate_log(command)

    if not replicated:
        return web.json_response({
            "success": False,
            "reason": "failed to replicate release command to majority"
        }, status=503)

    return web.json_response({
        "success": True,
        "resource": resource,
        "client_id": client_id,
        "message": "lock released and replicated using Raft"
    })


async def lock_status(request):
    lock_manager = request.app["lock_manager"]
    return web.json_response(lock_manager.get_status())


async def forward_to_owner(owner_url, endpoint, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{owner_url}{endpoint}",
            json=data,
            timeout=5
        ) as response:
            result = await response.json()
            return web.json_response(result, status=response.status)


async def queue_enqueue(request):
    queue_node = request.app["queue_node"]
    data = await request.json()

    queue_name = data.get("queue_name")
    payload = data.get("payload")
    producer_id = data.get("producer_id", "producer-default")

    if not queue_name or payload is None:
        return web.json_response({
            "success": False,
            "reason": "queue_name and payload are required"
        }, status=400)

    owner = queue_node.get_queue_owner(queue_name)

    if owner != queue_node.address:
        return await forward_to_owner(owner, "/queue/enqueue", data)

    result = await queue_node.enqueue(queue_name, payload, producer_id)
    return web.json_response(result)


async def queue_dequeue(request):
    queue_node = request.app["queue_node"]
    data = await request.json()

    queue_name = data.get("queue_name")
    consumer_id = data.get("consumer_id", "consumer-default")

    if not queue_name:
        return web.json_response({
            "success": False,
            "reason": "queue_name is required"
        }, status=400)

    owner = queue_node.get_queue_owner(queue_name)

    if owner != queue_node.address:
        return await forward_to_owner(owner, "/queue/dequeue", data)

    result = await queue_node.dequeue(queue_name, consumer_id)
    status_code = 200 if result["success"] else 404
    return web.json_response(result, status=status_code)


async def queue_ack(request):
    queue_node = request.app["queue_node"]
    data = await request.json()

    queue_name = data.get("queue_name")
    message_id = data.get("message_id")
    consumer_id = data.get("consumer_id")

    if not queue_name or not message_id or not consumer_id:
        return web.json_response({
            "success": False,
            "reason": "queue_name, message_id, and consumer_id are required"
        }, status=400)

    owner = queue_node.get_queue_owner(queue_name)

    if owner != queue_node.address:
        return await forward_to_owner(owner, "/queue/ack", data)

    result = await queue_node.ack(queue_name, message_id, consumer_id)
    status_code = 200 if result["success"] else 404
    return web.json_response(result, status=status_code)


async def queue_recover(request):
    queue_node = request.app["queue_node"]
    data = await request.json()

    queue_name = data.get("queue_name")

    if not queue_name:
        return web.json_response({
            "success": False,
            "reason": "queue_name is required"
        }, status=400)

    owner = queue_node.get_queue_owner(queue_name)

    if owner != queue_node.address:
        return await forward_to_owner(owner, "/queue/recover", data)

    result = await queue_node.recover_expired_messages(queue_name)
    return web.json_response(result)


async def queue_status(request):
    queue_node = request.app["queue_node"]
    queue_name = request.query.get("queue_name", "default")

    result = await queue_node.status(queue_name)
    return web.json_response(result)


async def cache_read(request):
    cache_node = request.app["cache_node"]
    key = request.match_info["key"]

    result = await cache_node.read(key)
    status_code = 200 if result["success"] else 404

    return web.json_response(result, status=status_code)


async def cache_write(request):
    cache_node = request.app["cache_node"]
    key = request.match_info["key"]
    data = await request.json()

    if "value" not in data:
        return web.json_response({
            "success": False,
            "reason": "value is required"
        }, status=400)

    client_id = data.get("client_id", "cache-client")
    propagation = data.get("propagation", "invalidate")

    if propagation not in ["invalidate", "update"]:
        return web.json_response({
            "success": False,
            "reason": "propagation must be invalidate or update"
        }, status=400)

    result = await cache_node.write(
        key=key,
        value=data["value"],
        client_id=client_id,
        propagation=propagation
    )

    return web.json_response(result)


async def cache_delete(request):
    cache_node = request.app["cache_node"]
    key = request.match_info["key"]

    result = await cache_node.delete(key)
    return web.json_response(result)


async def cache_internal_invalidate(request):
    cache_node = request.app["cache_node"]
    data = await request.json()

    result = await cache_node.invalidate(
        key=data["key"],
        source_node=data.get("source_node", "unknown")
    )

    return web.json_response(result)


async def cache_internal_update(request):
    cache_node = request.app["cache_node"]
    data = await request.json()

    result = await cache_node.update_from_peer(
        key=data["key"],
        value=data["value"],
        updated_at=data["updated_at"],
        source_node=data.get("source_node", "unknown")
    )

    return web.json_response(result)


async def cache_status(request):
    cache_node = request.app["cache_node"]
    return web.json_response(cache_node.status())


async def metrics(request):
    raft = request.app["raft"]
    lock_manager = request.app["lock_manager"]
    cache_node = request.app["cache_node"]

    return web.json_response({
        "raft": raft.get_status(),
        "lock_manager": lock_manager.get_status(),
        "cache": cache_node.status()
    })


async def on_startup(app):
    await app["raft"].start()


async def on_cleanup(app):
    await app["raft"].stop()
    await app["redis"].aclose()


def create_app():
    config = get_config()

    address = config.node_address

    redis_client = redis.Redis(
        host=config.redis_host,
        port=config.redis_port,
        db=config.redis_db
    )

    app = web.Application()
    app["config"] = config
    app["redis"] = redis_client

    raft = RaftNode(
        node_id=config.node_id,
        address=address,
        cluster_nodes=config.cluster_nodes
    )

    lock_manager = DistributedLockManager()
    raft.apply_callback = lock_manager.apply_command

    queue_node = DistributedQueueNode(
        node_id=config.node_id,
        address=address,
        cluster_nodes=config.cluster_nodes,
        redis_client=redis_client
    )

    cache_node = DistributedCacheNode(
        node_id=config.node_id,
        address=address,
        cluster_nodes=config.cluster_nodes,
        redis_client=redis_client,
        capacity=3
    )

    app["raft"] = raft
    app["lock_manager"] = lock_manager
    app["queue_node"] = queue_node
    app["cache_node"] = cache_node

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    app.router.add_get("/raft/status", raft_status)
    app.router.add_post("/raft/request-vote", request_vote)
    app.router.add_post("/raft/append-entries", append_entries)

    app.router.add_post("/partition/enable", enable_partition)
    app.router.add_post("/partition/disable", disable_partition)

    app.router.add_post("/lock/acquire", acquire_lock)
    app.router.add_post("/lock/release", release_lock)
    app.router.add_get("/lock/status", lock_status)

    app.router.add_post("/queue/enqueue", queue_enqueue)
    app.router.add_post("/queue/dequeue", queue_dequeue)
    app.router.add_post("/queue/ack", queue_ack)
    app.router.add_post("/queue/recover", queue_recover)
    app.router.add_get("/queue/status", queue_status)

    app.router.add_get("/cache/status", cache_status)
    app.router.add_get("/cache/{key}", cache_read)
    app.router.add_post("/cache/{key}", cache_write)
    app.router.add_delete("/cache/{key}", cache_delete)
    app.router.add_post("/cache/internal/invalidate", cache_internal_invalidate)
    app.router.add_post("/cache/internal/update", cache_internal_update)

    app.router.add_get("/metrics", metrics)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


if __name__ == "__main__":
    config = get_config()
    app = create_app()

    print(f"Starting {config.node_id} on {config.node_host}:{config.node_port}")

    web.run_app(
        app,
        host=config.node_host,
        port=config.node_port
    )
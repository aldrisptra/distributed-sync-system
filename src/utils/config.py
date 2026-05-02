import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    node_id: str
    node_host: str
    node_port: int
    node_address: str
    cluster_nodes: list[str]
    redis_host: str
    redis_port: int
    redis_db: int
    api_key: str
    log_level: str


def get_config() -> Config:
    node_id = os.getenv("NODE_ID", "node1")
    node_host = os.getenv("NODE_HOST", "127.0.0.1")
    node_port = int(os.getenv("NODE_PORT", "8001"))

    if node_host == "0.0.0.0":
        default_node_address = f"http://{node_id}:{node_port}"
    else:
        default_node_address = f"http://{node_host}:{node_port}"

    cluster_nodes_raw = os.getenv(
        "CLUSTER_NODES",
        "http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"
    )

    return Config(
        node_id=node_id,
        node_host=node_host,
        node_port=node_port,
        node_address=os.getenv("NODE_ADDRESS", default_node_address),
        cluster_nodes=[
            node.strip()
            for node in cluster_nodes_raw.split(",")
            if node.strip()
        ],
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        api_key=os.getenv("API_KEY", "distributed-secret-key"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
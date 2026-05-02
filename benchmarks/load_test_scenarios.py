from locust import HttpUser, task, between
import random


class DistributedSyncUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client_id = f"client-{random.randint(1, 10000)}"
        self.consumer_id = f"consumer-{random.randint(1, 10000)}"
        self.producer_id = f"producer-{random.randint(1, 10000)}"

    @task(2)
    def test_health_check(self):
        self.client.get("/health", name="Health Check")

    @task(3)
    def test_raft_status(self):
        self.client.get("/raft/status", name="Raft Status")

    @task(4)
    def test_queue_enqueue(self):
        payload = {
            "queue_name": "benchmark-orders",
            "producer_id": self.producer_id,
            "payload": {
                "order_id": random.randint(1, 100000),
                "item": random.choice(["laptop", "keyboard", "mouse", "monitor"])
            }
        }

        self.client.post(
            "/queue/enqueue",
            json=payload,
            name="Queue Enqueue"
        )

    @task(3)
    def test_queue_dequeue(self):
        payload = {
            "queue_name": "benchmark-orders",
            "consumer_id": self.consumer_id
        }

        response = self.client.post(
            "/queue/dequeue",
            json=payload,
            name="Queue Dequeue"
        )

        if response.status_code == 200:
            data = response.json()
            message_id = data.get("message_id")

            if message_id:
                ack_payload = {
                    "queue_name": "benchmark-orders",
                    "message_id": message_id,
                    "consumer_id": self.consumer_id
                }

                self.client.post(
                    "/queue/ack",
                    json=ack_payload,
                    name="Queue ACK"
                )

    @task(3)
    def test_cache_write(self):
        key = f"benchmark-key-{random.randint(1, 20)}"

        payload = {
            "client_id": self.client_id,
            "value": {
                "number": random.randint(1, 1000),
                "source": "locust"
            },
            "propagation": "invalidate"
        }

        self.client.post(
            f"/cache/{key}",
            json=payload,
            name="Cache Write"
        )

@task(5)
def test_cache_read(self):
    key = f"benchmark-key-{random.randint(1, 20)}"

    with self.client.get(
        f"/cache/{key}",
        name="Cache Read",
        catch_response=True
    ) as response:
        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Unexpected status code: {response.status_code}")
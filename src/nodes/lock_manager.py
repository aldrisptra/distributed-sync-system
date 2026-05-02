from typing import Dict, Set, Optional, Any


class DistributedLockManager:
    def __init__(self):
        self.locks: Dict[str, Dict[str, Any]] = {}
        self.wait_for_graph: Dict[str, Set[str]] = {}

    def _get_lock_state(self, resource: str) -> Dict[str, Any]:
        if resource not in self.locks:
            self.locks[resource] = {
                "shared_holders": set(),
                "exclusive_holder": None
            }

        return self.locks[resource]

    def _detect_cycle(self) -> bool:
        visited = set()
        recursion_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            recursion_stack.add(node)

            for neighbor in self.wait_for_graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True

            recursion_stack.remove(node)
            return False

        for node in self.wait_for_graph:
            if node not in visited:
                if dfs(node):
                    return True

        return False

    def _add_wait_edges(self, client_id: str, holders: Set[str]):
        if client_id not in self.wait_for_graph:
            self.wait_for_graph[client_id] = set()

        for holder in holders:
            if holder != client_id:
                self.wait_for_graph[client_id].add(holder)

    def _clear_wait_edges(self, client_id: str):
        self.wait_for_graph.pop(client_id, None)

    def acquire_lock(
        self,
        resource: str,
        client_id: str,
        lock_type: str
    ) -> Dict[str, Any]:
        if lock_type not in ["shared", "exclusive"]:
            return {
                "success": False,
                "reason": "lock_type must be shared or exclusive"
            }

        lock_state = self._get_lock_state(resource)
        shared_holders: Set[str] = lock_state["shared_holders"]
        exclusive_holder: Optional[str] = lock_state["exclusive_holder"]

        if lock_type == "shared":
            if exclusive_holder is None or exclusive_holder == client_id:
                shared_holders.add(client_id)
                self._clear_wait_edges(client_id)

                return {
                    "success": True,
                    "resource": resource,
                    "client_id": client_id,
                    "lock_type": lock_type,
                    "message": "shared lock acquired"
                }

            self._add_wait_edges(client_id, {exclusive_holder})

        if lock_type == "exclusive":
            blocking_holders = set(shared_holders)

            if exclusive_holder:
                blocking_holders.add(exclusive_holder)

            blocking_holders.discard(client_id)

            if not blocking_holders:
                lock_state["exclusive_holder"] = client_id
                shared_holders.discard(client_id)
                self._clear_wait_edges(client_id)

                return {
                    "success": True,
                    "resource": resource,
                    "client_id": client_id,
                    "lock_type": lock_type,
                    "message": "exclusive lock acquired"
                }

            self._add_wait_edges(client_id, blocking_holders)

        if self._detect_cycle():
            return {
                "success": False,
                "resource": resource,
                "client_id": client_id,
                "lock_type": lock_type,
                "reason": "deadlock detected"
            }

        return {
            "success": False,
            "resource": resource,
            "client_id": client_id,
            "lock_type": lock_type,
            "reason": "lock is currently held by another client"
        }

    def release_lock(
        self,
        resource: str,
        client_id: str
    ) -> Dict[str, Any]:
        if resource not in self.locks:
            return {
                "success": False,
                "reason": "resource does not exist"
            }

        lock_state = self.locks[resource]
        shared_holders: Set[str] = lock_state["shared_holders"]

        released = False

        if client_id in shared_holders:
            shared_holders.remove(client_id)
            released = True

        if lock_state["exclusive_holder"] == client_id:
            lock_state["exclusive_holder"] = None
            released = True

        self._clear_wait_edges(client_id)

        if not released:
            return {
                "success": False,
                "resource": resource,
                "client_id": client_id,
                "reason": "client does not hold this lock"
            }

        return {
            "success": True,
            "resource": resource,
            "client_id": client_id,
            "message": "lock released"
        }

    def get_status(self) -> Dict[str, Any]:
        clean_locks = {}

        for resource, state in self.locks.items():
            clean_locks[resource] = {
                "shared_holders": list(state["shared_holders"]),
                "exclusive_holder": state["exclusive_holder"]
            }

        clean_wait_graph = {
            client: list(waiting_for)
            for client, waiting_for in self.wait_for_graph.items()
        }

        return {
            "locks": clean_locks,
            "wait_for_graph": clean_wait_graph,
            "deadlock_detected": self._detect_cycle()
        }

    def apply_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        command_type = command.get("type")

        if command_type == "acquire_lock":
            return self.acquire_lock(
                resource=command["resource"],
                client_id=command["client_id"],
                lock_type=command["lock_type"]
            )

        if command_type == "release_lock":
            return self.release_lock(
                resource=command["resource"],
                client_id=command["client_id"]
            )

        return {
            "success": False,
            "reason": "unknown lock command"
        }
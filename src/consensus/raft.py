import asyncio
import random
import time
from typing import Any, Dict, List, Optional

from src.nodes.base_node import BaseNode


class RaftNode(BaseNode):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

    def __init__(self, node_id: str, address: str, cluster_nodes: List[str]):
        super().__init__(node_id, address, cluster_nodes)

        self.state = self.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.leader_id: Optional[str] = None

        self.log: List[Dict[str, Any]] = []
        self.commit_index = -1
        self.last_applied = -1
        self.apply_callback = None

        self.last_heartbeat = time.time()
        self.election_timeout = self._new_election_timeout()

        self.partitioned = False
        self.running = False
        self.tasks: List[asyncio.Task] = []

    def _new_election_timeout(self) -> float:
        return random.uniform(3.0, 6.0)

    def get_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "state": self.state,
            "term": self.current_term,
            "voted_for": self.voted_for,
            "leader_id": self.leader_id,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "partitioned": self.partitioned,
            "peers": self.peer_nodes
        }

    async def start(self):
        if self.running:
            return

        self.running = True
        self.tasks = [
            asyncio.create_task(self._election_loop()),
            asyncio.create_task(self._heartbeat_loop())
        ]

    async def stop(self):
        self.running = False

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def _election_loop(self):
        while self.running:
            await asyncio.sleep(0.5)

            if self.partitioned:
                continue

            if self.state == self.LEADER:
                continue

            elapsed = time.time() - self.last_heartbeat

            if elapsed >= self.election_timeout:
                await self.start_election()

    async def _heartbeat_loop(self):
        while self.running:
            await asyncio.sleep(1)

            if self.partitioned:
                continue

            if self.state == self.LEADER:
                await self.send_heartbeats()

    async def start_election(self):
        self.state = self.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.leader_id = None
        self.election_timeout = self._new_election_timeout()

        votes = 1

        payload = {
            "term": self.current_term,
            "candidate_id": self.node_id,
            "last_log_index": len(self.log) - 1,
            "last_log_term": self.log[-1]["term"] if self.log else 0
        }

        responses = await self.broadcast("/raft/request-vote", payload)

        for response in responses:
            if not response:
                continue

            response_term = response.get("term", 0)

            if response_term > self.current_term:
                self.become_follower(response_term)
                return

            if response.get("vote_granted"):
                votes += 1

        majority = (len(self.cluster_nodes) // 2) + 1

        if votes >= majority:
            self.state = self.LEADER
            self.leader_id = self.node_id
            await self.send_heartbeats()
        else:
            self.state = self.FOLLOWER

    def become_follower(self, term: int, leader_id: Optional[str] = None):
        self.state = self.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.leader_id = leader_id
        self.last_heartbeat = time.time()
        self.election_timeout = self._new_election_timeout()

    async def handle_request_vote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.partitioned:
            return {
                "term": self.current_term,
                "vote_granted": False,
                "reason": "node is partitioned"
            }

        candidate_term = data.get("term", 0)
        candidate_id = data.get("candidate_id")

        if candidate_term < self.current_term:
            return {
                "term": self.current_term,
                "vote_granted": False
            }

        if candidate_term > self.current_term:
            self.become_follower(candidate_term)

        can_vote = self.voted_for is None or self.voted_for == candidate_id

        if can_vote:
            self.voted_for = candidate_id
            self.last_heartbeat = time.time()
            return {
                "term": self.current_term,
                "vote_granted": True
            }

        return {
            "term": self.current_term,
            "vote_granted": False
        }

    async def send_heartbeats(self):
        payload = {
            "term": self.current_term,
            "leader_id": self.node_id,
            "entries": [],
            "leader_commit": self.commit_index
        }

        await self.broadcast("/raft/append-entries", payload)

    async def handle_append_entries(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.partitioned:
            return {
                "term": self.current_term,
                "success": False,
                "reason": "node is partitioned"
            }

        leader_term = data.get("term", 0)
        leader_id = data.get("leader_id")

        if leader_term < self.current_term:
            return {
                "term": self.current_term,
                "success": False
            }

        if leader_term >= self.current_term:
            self.become_follower(leader_term, leader_id)

        entries = data.get("entries", [])

        for entry in entries:
            self.log.append(entry)

        leader_commit = data.get("leader_commit", -1)

        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log) - 1)

        self.apply_committed_entries()

        return {
            "term": self.current_term,
            "success": True
        }

    def apply_committed_entries(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1

            if self.last_applied >= len(self.log):
                break

            entry = self.log[self.last_applied]
            command = entry.get("command")

            if self.apply_callback and command:
                self.apply_callback(command)

    async def replicate_log(self, command: Dict[str, Any]) -> bool:
        if self.state != self.LEADER:
            return False

        entry = {
            "term": self.current_term,
            "command": command
        }

        self.log.append(entry)
        entry_index = len(self.log) - 1

        payload = {
            "term": self.current_term,
            "leader_id": self.node_id,
            "entries": [entry],
            "leader_commit": entry_index
        }

        responses = await self.broadcast("/raft/append-entries", payload)

        success_count = 1

        for response in responses:
            if response and response.get("success"):
                success_count += 1

        majority = (len(self.cluster_nodes) // 2) + 1

        if success_count >= majority:
            self.commit_index = entry_index
            self.apply_committed_entries()
            return True

        return False
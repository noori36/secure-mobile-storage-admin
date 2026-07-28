
import time
import uuid
from typing import Dict, List, Tuple
import httpx
from fastapi import HTTPException
from .config import AppConfig
from .consistent_hash import ConsistentHashRing
from .models import HealthStatus, NodeState, RequestPriority, WriteObjectRequest
from .scoring import calculate_score
from .state import ClusterState

class StorageRouter:
    def __init__(self, state: ClusterState, ring: ConsistentHashRing, config: AppConfig):
        self.state = state
        self.ring = ring
        self.config = config

    def _candidate_nodes_by_ids(self, node_ids: List[str], request_type: str) -> List[NodeState]:
        candidates: List[NodeState] = []
        for node_id in node_ids:
            node = self.state.get_node(node_id)
            if not node:
                continue
            if node.health not in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}:
                continue
            if node.circuit_open:
                continue
            if request_type == "READ" and not node.can_accept_reads:
                continue
            if request_type == "WRITE" and not node.can_accept_writes:
                continue
            candidates.append(node)
        return candidates

    def _sort_by_score(
        self,
        candidates: List[NodeState],
        request_type: str,
        priority: RequestPriority = RequestPriority.normal
    ) -> List[Tuple[float, NodeState]]:
        scored = [
            (calculate_score(node, request_type=request_type, priority=priority), node)
            for node in candidates
        ]
        return sorted(scored, key=lambda item: item[0])

    def _mark_node_failure(self, node: NodeState, error: str):
        node.failed_requests += 1
        node.last_error = error
        if node.failed_requests >= 3:
            node.health = HealthStatus.SUSPECT
            node.circuit_open = True

    async def write_object(self, request: WriteObjectRequest):
        if request.request_id is None:
            request.request_id = str(uuid.uuid4())
        if request.idempotency_key is None:
            request.idempotency_key = request.request_id

        preferred_replica_ids = self.ring.get_replicas(
            request.object_id,
            self.config.replication_factor
        )
        preferred_candidates = self._candidate_nodes_by_ids(preferred_replica_ids, "WRITE")

        # If preferred hash replicas are unavailable, use other healthy writable nodes.
        if len(preferred_candidates) < self.config.write_quorum:
            extra_ids = [
                node.id for node in self.state.routable_nodes()
                if node.id not in preferred_replica_ids and node.can_accept_writes
            ]
            preferred_candidates.extend(self._candidate_nodes_by_ids(extra_ids, "WRITE"))

        if not preferred_candidates:
            self.state.record_failure()
            raise HTTPException(status_code=503, detail="No writable storage nodes available")

        sorted_candidates = self._sort_by_score(preferred_candidates, "WRITE", request.priority)

        acknowledgments = 0
        successful_replicas: List[str] = []
        versions: Dict[str, int] = {}
        errors: Dict[str, str] = {}

        async with httpx.AsyncClient(timeout=3.0) as client:
            for _, node in sorted_candidates:
                if acknowledgments >= self.config.replication_factor:
                    break
                try:
                    start = time.perf_counter()
                    response = await client.post(
                        f"{node.url}/write",
                        json={
                            "object_id": request.object_id,
                            "payload": request.payload,
                            "size_mb": request.size_mb,
                            "request_id": request.request_id,
                            "idempotency_key": request.idempotency_key,
                        },
                    )
                    latency_ms = (time.perf_counter() - start) * 1000

                    if response.status_code != 200:
                        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

                    data = response.json()
                    acknowledgments += 1
                    successful_replicas.append(node.id)
                    versions[node.id] = int(data.get("version", 0))
                    node.successful_requests += 1
                    node.avg_latency_ms = round((0.8 * node.avg_latency_ms) + (0.2 * latency_ms), 2)

                except Exception as exc:
                    errors[node.id] = str(exc)
                    self._mark_node_failure(node, str(exc))

        if acknowledgments < self.config.write_quorum:
            self.state.record_failure()
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Write quorum not reached",
                    "required_quorum": self.config.write_quorum,
                    "acknowledgments": acknowledgments,
                    "successful_replicas": successful_replicas,
                    "errors": errors,
                },
            )

        self.state.update_object_metadata(
            object_id=request.object_id,
            replicas=successful_replicas,
            versions=versions,
            size_mb=request.size_mb,
        )
        self.state.record_success()

        return {
            "object_id": request.object_id,
            "status": "OK",
            "replicas": successful_replicas,
            "acknowledgments": acknowledgments,
            "replication_factor": self.config.replication_factor,
            "write_quorum": self.config.write_quorum,
            "request_id": request.request_id,
            "preferred_hash_replicas": preferred_replica_ids,
        }

    async def read_object(self, object_id: str, priority: RequestPriority = RequestPriority.normal):
        metadata = self.state.get_object_metadata(object_id)
        if metadata:
            candidate_ids = metadata.replicas
        else:
            candidate_ids = self.ring.get_replicas(object_id, self.config.replication_factor)

        candidates = self._candidate_nodes_by_ids(candidate_ids, "READ")
        if not candidates:
            self.state.record_failure()
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "No readable replicas available",
                    "object_id": object_id,
                    "candidate_ids": candidate_ids,
                },
            )

        sorted_candidates = self._sort_by_score(candidates, "READ", priority)
        errors: Dict[str, str] = {}

        async with httpx.AsyncClient(timeout=3.0) as client:
            for _, node in sorted_candidates:
                try:
                    start = time.perf_counter()
                    response = await client.get(f"{node.url}/read/{object_id}")
                    latency_ms = (time.perf_counter() - start) * 1000

                    if response.status_code != 200:
                        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

                    data = response.json()
                    node.successful_requests += 1
                    node.avg_latency_ms = round((0.8 * node.avg_latency_ms) + (0.2 * latency_ms), 2)
                    self.state.record_success()

                    return {
                        "object_id": object_id,
                        "payload": data["payload"],
                        "node_id": node.id,
                        "version": data.get("version"),
                        "replica_candidates": candidate_ids,
                        "selected_node": node.id,
                    }

                except Exception as exc:
                    errors[node.id] = str(exc)
                    self._mark_node_failure(node, str(exc))

        self.state.record_failure()
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Read failed on all replicas",
                "object_id": object_id,
                "errors": errors,
            },
        )

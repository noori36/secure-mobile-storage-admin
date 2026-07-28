
from typing import Dict, List, Optional
from .models import HealthStatus, NodeConfig, NodeState, ObjectMetadata

class ClusterState:
    def __init__(self, node_configs: List[NodeConfig]):
        self.nodes: Dict[str, NodeState] = {
            cfg.id: NodeState(**cfg.model_dump()) for cfg in node_configs
        }
        self.metadata: Dict[str, ObjectMetadata] = {}
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    def get_node(self, node_id: str) -> Optional[NodeState]:
        return self.nodes.get(node_id)

    def routable_nodes(self) -> List[NodeState]:
        allowed = {HealthStatus.HEALTHY, HealthStatus.DEGRADED}
        return [
            n for n in self.nodes.values()
            if n.health in allowed and not n.circuit_open
        ]

    def mark_disabled(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].health = HealthStatus.DISABLED
            self.nodes[node_id].last_error = "Manually disabled"

    def mark_enabled(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].health = HealthStatus.UNKNOWN
            self.nodes[node_id].last_error = None
            self.nodes[node_id].circuit_open = False
            self.nodes[node_id].failed_requests = 0

    def update_object_metadata(self, object_id: str, replicas: List[str], versions: Dict[str, int], size_mb: int):
        self.metadata[object_id] = ObjectMetadata(
            object_id=object_id,
            replicas=replicas,
            version_by_node=versions,
            size_mb=size_mb,
        )

    def get_object_metadata(self, object_id: str) -> Optional[ObjectMetadata]:
        return self.metadata.get(object_id)

    def record_success(self):
        self.total_requests += 1
        self.successful_requests += 1

    def record_failure(self):
        self.total_requests += 1
        self.failed_requests += 1

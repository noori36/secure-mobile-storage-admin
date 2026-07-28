
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    SUSPECT = "SUSPECT"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"

class RequestPriority(str, Enum):
    high = "high"
    normal = "normal"
    low = "low"

class NodeConfig(BaseModel):
    id: str
    url: str
    capacity_mb: int = 10000
    can_accept_reads: bool = True
    can_accept_writes: bool = True

class NodeState(NodeConfig):
    health: HealthStatus = HealthStatus.UNKNOWN
    current_load: float = 0.0
    avg_latency_ms: float = 0.0
    queue_depth: int = 0
    disk_usage_percent: float = 0.0
    active_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_heartbeat: Optional[float] = None
    last_error: Optional[str] = None
    circuit_open: bool = False

class WriteObjectRequest(BaseModel):
    object_id: str = Field(..., description="Unique object key")
    payload: str
    size_mb: int = 1
    priority: RequestPriority = RequestPriority.normal
    request_id: Optional[str] = None
    idempotency_key: Optional[str] = None

class ObjectMetadata(BaseModel):
    object_id: str
    replicas: List[str]
    version_by_node: Dict[str, int] = {}
    size_mb: int = 0

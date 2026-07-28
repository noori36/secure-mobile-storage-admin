
from typing import Dict
from .models import HealthStatus, NodeState, RequestPriority

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))

def health_penalty(status: HealthStatus) -> float:
    return {
        HealthStatus.HEALTHY: 0,
        HealthStatus.DEGRADED: 35,
        HealthStatus.SUSPECT: 65,
        HealthStatus.UNKNOWN: 80,
        HealthStatus.UNHEALTHY: 100,
        HealthStatus.DISABLED: 100,
    }.get(status, 100)

def priority_weights(priority: RequestPriority, request_type: str) -> Dict[str, float]:
    if request_type == "READ":
        if priority == RequestPriority.high:
            return {"load": 0.20, "latency": 0.50, "queue": 0.20, "disk": 0.00, "health": 0.10}
        if priority == RequestPriority.low:
            return {"load": 0.45, "latency": 0.25, "queue": 0.20, "disk": 0.00, "health": 0.10}
        return {"load": 0.25, "latency": 0.40, "queue": 0.20, "disk": 0.00, "health": 0.15}

    if priority == RequestPriority.high:
        return {"load": 0.20, "latency": 0.25, "queue": 0.25, "disk": 0.20, "health": 0.10}
    if priority == RequestPriority.low:
        return {"load": 0.35, "latency": 0.15, "queue": 0.25, "disk": 0.15, "health": 0.10}
    return {"load": 0.20, "latency": 0.15, "queue": 0.25, "disk": 0.30, "health": 0.10}

def calculate_score(node: NodeState, request_type: str, priority: RequestPriority = RequestPriority.normal) -> float:
    latency_score = clamp((node.avg_latency_ms / 500) * 100)
    load_score = clamp(node.current_load)
    queue_score = clamp((node.queue_depth / 50) * 100)
    disk_score = clamp(node.disk_usage_percent)
    node_health_penalty = health_penalty(node.health)
    weights = priority_weights(priority, request_type)
    score = (
        weights["load"] * load_score
        + weights["latency"] * latency_score
        + weights["queue"] * queue_score
        + weights["disk"] * disk_score
        + weights["health"] * node_health_penalty
    )
    if node.circuit_open:
        score += 1000
    return round(score, 4)

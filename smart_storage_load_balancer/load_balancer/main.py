
import asyncio
from fastapi import FastAPI, HTTPException, Query
from .config import load_config
from .consistent_hash import ConsistentHashRing
from .health_checker import HealthChecker
from .models import RequestPriority, WriteObjectRequest
from .scoring import calculate_score
from .state import ClusterState
from .router import StorageRouter

config = load_config()
state = ClusterState(config.nodes)
ring = ConsistentHashRing([node.id for node in config.nodes], virtual_nodes=config.virtual_nodes)
router = StorageRouter(state=state, ring=ring, config=config)
health_checker = HealthChecker(state=state, config=config)

app = FastAPI(title="Smart Storage Load Balancer")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(health_checker.start())

@app.get("/")
async def root():
    return {
        "service": "smart-storage-load-balancer",
        "message": "Use /docs for Swagger UI",
        "endpoints": [
            "POST /object",
            "GET /object/{object_id}",
            "GET /nodes",
            "GET /metrics",
            "POST /admin/nodes/{node_id}/disable",
            "POST /admin/nodes/{node_id}/enable",
            "GET /hash-ring",
        ],
    }

@app.get("/health")
async def health():
    return {
        "status": "OK",
        "known_nodes": len(state.nodes),
        "routable_nodes": len(state.routable_nodes()),
    }

@app.post("/object")
async def write_object(request: WriteObjectRequest):
    return await router.write_object(request)

@app.get("/object/{object_id}")
async def read_object(
    object_id: str,
    priority: RequestPriority = Query(default=RequestPriority.normal),
):
    return await router.read_object(object_id=object_id, priority=priority)

@app.get("/nodes")
async def nodes():
    response = []
    for node in state.nodes.values():
        response.append({
            **node.model_dump(),
            "read_score": calculate_score(node, "READ"),
            "write_score": calculate_score(node, "WRITE"),
        })
    return response

@app.get("/metadata")
async def metadata():
    return {
        key: value.model_dump()
        for key, value in state.metadata.items()
    }

@app.get("/metrics")
async def metrics():
    success_rate = 0
    if state.total_requests:
        success_rate = state.successful_requests / state.total_requests

    return {
        "load_balancer": {
            "total_requests": state.total_requests,
            "successful_requests": state.successful_requests,
            "failed_requests": state.failed_requests,
            "success_rate": round(success_rate, 4),
        },
        "nodes": [
            {
                "id": node.id,
                "health": node.health,
                "current_load": node.current_load,
                "avg_latency_ms": node.avg_latency_ms,
                "queue_depth": node.queue_depth,
                "disk_usage_percent": node.disk_usage_percent,
                "circuit_open": node.circuit_open,
                "last_error": node.last_error,
                "read_score": calculate_score(node, "READ"),
                "write_score": calculate_score(node, "WRITE"),
            }
            for node in state.nodes.values()
        ],
    }

@app.get("/hash-ring")
async def hash_ring():
    return ring.snapshot()

@app.get("/placement/{object_id}")
async def placement(object_id: str):
    expected = ring.get_replicas(object_id, config.replication_factor)
    actual = state.get_object_metadata(object_id)
    return {
        "object_id": object_id,
        "consistent_hash_replicas": expected,
        "metadata": actual.model_dump() if actual else None,
    }

@app.post("/admin/nodes/{node_id}/disable")
async def disable_node(node_id: str):
    if node_id not in state.nodes:
        raise HTTPException(status_code=404, detail="Unknown node")
    state.mark_disabled(node_id)
    ring.remove_node(node_id)
    return {
        "status": "OK",
        "message": f"{node_id} disabled and removed from hash ring",
    }

@app.post("/admin/nodes/{node_id}/enable")
async def enable_node(node_id: str):
    if node_id not in state.nodes:
        raise HTTPException(status_code=404, detail="Unknown node")
    state.mark_enabled(node_id)
    ring.add_node(node_id)
    return {
        "status": "OK",
        "message": f"{node_id} enabled and added back to hash ring",
    }

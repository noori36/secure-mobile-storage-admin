
import asyncio
import os
import random
import time
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

NODE_ID = os.getenv("NODE_ID", "node-a")
NODE_PORT = int(os.getenv("NODE_PORT", "8001"))
BASE_LATENCY_MS = int(os.getenv("BASE_LATENCY_MS", "20"))
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.01"))
CAPACITY_MB = int(os.getenv("CAPACITY_MB", "10000"))

app = FastAPI(title=f"Simulated Storage Node {NODE_ID}")
OBJECT_STORE: Dict[str, dict] = {}
IDEMPOTENCY_STORE: Dict[str, dict] = {}
STATE = {
    "node_id": NODE_ID,
    "started_at": time.time(),
    "active_requests": 0,
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "failure_mode": False,
    "base_latency_ms": BASE_LATENCY_MS,
    "failure_rate": FAILURE_RATE,
    "capacity_mb": CAPACITY_MB,
    "used_mb": 0,
    "last_error": None,
}

class WriteRequest(BaseModel):
    object_id: str
    payload: str
    size_mb: int = 1
    request_id: str
    idempotency_key: Optional[str] = None

class FailureModeRequest(BaseModel):
    enabled: bool

def current_load_percent() -> float:
    active_component = min(STATE["active_requests"] * 12, 80)
    random_noise = random.uniform(0, 10)
    return round(min(active_component + random_noise, 100), 2)

def queue_depth() -> int:
    return int(STATE["active_requests"] + random.randint(0, 3))

def disk_usage_percent() -> float:
    return round((STATE["used_mb"] / STATE["capacity_mb"]) * 100, 2)

async def simulate_storage_delay():
    dynamic_latency_ms = STATE["base_latency_ms"] + (STATE["active_requests"] * 8)
    jitter_ms = random.randint(0, 25)
    await asyncio.sleep((dynamic_latency_ms + jitter_ms) / 1000)

def should_fail() -> bool:
    if STATE["failure_mode"]:
        return True
    return random.random() < STATE["failure_rate"]

async def process_guard():
    STATE["active_requests"] += 1
    STATE["total_requests"] += 1
    await simulate_storage_delay()
    if should_fail():
        STATE["failed_requests"] += 1
        STATE["last_error"] = "Simulated node failure"
        STATE["active_requests"] -= 1
        raise HTTPException(status_code=503, detail="Simulated storage node failure")

@app.get("/health")
async def health():
    start = time.perf_counter()
    await asyncio.sleep(STATE["base_latency_ms"] / 1000)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    if STATE["failure_mode"]:
        raise HTTPException(status_code=503, detail="Node is in forced failure mode")
    usage = disk_usage_percent()
    status = "HEALTHY"
    if usage >= 95:
        status = "UNHEALTHY"
    elif usage >= 85:
        status = "DEGRADED"
    return {
        "node_id": NODE_ID,
        "status": status,
        "latency_ms": latency_ms,
        "current_load": current_load_percent(),
        "queue_depth": queue_depth(),
        "disk_usage_percent": usage,
        "active_requests": STATE["active_requests"],
        "capacity_mb": STATE["capacity_mb"],
        "used_mb": STATE["used_mb"],
        "can_accept_reads": True,
        "can_accept_writes": usage < 95,
        "timestamp": time.time(),
    }

@app.get("/read/{object_id}")
async def read_object(object_id: str):
    await process_guard()
    try:
        if object_id not in OBJECT_STORE:
            STATE["failed_requests"] += 1
            raise HTTPException(status_code=404, detail=f"Object {object_id} not found on {NODE_ID}")
        STATE["successful_requests"] += 1
        record = OBJECT_STORE[object_id]
        return {
            "status": "OK",
            "node_id": NODE_ID,
            "object_id": object_id,
            "payload": record["payload"],
            "version": record["version"],
            "size_mb": record["size_mb"],
        }
    finally:
        STATE["active_requests"] -= 1

@app.post("/write")
async def write_object(request: WriteRequest):
    await process_guard()
    try:
        key = request.idempotency_key or request.request_id
        if key in IDEMPOTENCY_STORE:
            return IDEMPOTENCY_STORE[key]
        if disk_usage_percent() >= 95:
            STATE["failed_requests"] += 1
            raise HTTPException(status_code=507, detail="Insufficient storage capacity")
        previous = OBJECT_STORE.get(request.object_id)
        old_size = previous["size_mb"] if previous else 0
        new_used = STATE["used_mb"] - old_size + request.size_mb
        if new_used > STATE["capacity_mb"]:
            STATE["failed_requests"] += 1
            raise HTTPException(status_code=507, detail="Node capacity exceeded")
        version = int(time.time() * 1000)
        OBJECT_STORE[request.object_id] = {
            "object_id": request.object_id,
            "payload": request.payload,
            "size_mb": request.size_mb,
            "version": version,
            "request_id": request.request_id,
            "written_at": time.time(),
        }
        STATE["used_mb"] = new_used
        STATE["successful_requests"] += 1
        result = {
            "status": "OK",
            "node_id": NODE_ID,
            "object_id": request.object_id,
            "version": version,
            "size_mb": request.size_mb,
            "message": f"Object stored on {NODE_ID}",
        }
        IDEMPOTENCY_STORE[key] = result
        return result
    finally:
        STATE["active_requests"] -= 1

@app.get("/metrics")
async def metrics():
    total = max(STATE["total_requests"], 1)
    return {
        "node_id": NODE_ID,
        "active_requests": STATE["active_requests"],
        "total_requests": STATE["total_requests"],
        "successful_requests": STATE["successful_requests"],
        "failed_requests": STATE["failed_requests"],
        "error_rate": round(STATE["failed_requests"] / total, 4),
        "current_load": current_load_percent(),
        "queue_depth": queue_depth(),
        "disk_usage_percent": disk_usage_percent(),
        "object_count": len(OBJECT_STORE),
        "capacity_mb": STATE["capacity_mb"],
        "used_mb": STATE["used_mb"],
        "failure_mode": STATE["failure_mode"],
        "last_error": STATE["last_error"],
    }

@app.post("/admin/failure-mode")
async def set_failure_mode(request: FailureModeRequest):
    STATE["failure_mode"] = request.enabled
    return {"node_id": NODE_ID, "failure_mode": STATE["failure_mode"]}

@app.delete("/admin/object/{object_id}")
async def delete_object(object_id: str):
    if object_id not in OBJECT_STORE:
        raise HTTPException(status_code=404, detail="Object not found")
    removed = OBJECT_STORE.pop(object_id)
    STATE["used_mb"] = max(STATE["used_mb"] - removed["size_mb"], 0)
    return {"status": "OK", "node_id": NODE_ID, "deleted": object_id}

@app.get("/")
async def root():
    return {"service": "simulated-storage-node", "node_id": NODE_ID, "port": NODE_PORT}

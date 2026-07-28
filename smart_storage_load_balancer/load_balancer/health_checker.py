
import asyncio
import time
import httpx
from .config import AppConfig
from .models import HealthStatus
from .state import ClusterState

class HealthChecker:
    def __init__(self, state: ClusterState, config: AppConfig):
        self.state = state
        self.config = config
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            await self.check_all_nodes()
            await asyncio.sleep(self.config.health_check_interval_seconds)

    async def check_all_nodes(self):
        async with httpx.AsyncClient(timeout=self.config.health_timeout_seconds) as client:
            tasks = [self.check_node(client, node_id) for node_id in self.state.nodes.keys()]
            await asyncio.gather(*tasks)

    async def check_node(self, client: httpx.AsyncClient, node_id: str):
        node = self.state.nodes[node_id]
        if node.health == HealthStatus.DISABLED:
            return
        start = time.perf_counter()
        try:
            response = await client.get(f"{node.url}/health")
            latency_ms = (time.perf_counter() - start) * 1000
            if response.status_code != 200:
                node.health = HealthStatus.UNHEALTHY
                node.last_error = f"Health check HTTP {response.status_code}"
                node.circuit_open = True
                return

            data = response.json()
            node.avg_latency_ms = float(data.get("latency_ms", latency_ms))
            node.current_load = float(data.get("current_load", 0))
            node.queue_depth = int(data.get("queue_depth", 0))
            node.disk_usage_percent = float(data.get("disk_usage_percent", 0))
            node.active_requests = int(data.get("active_requests", 0))
            node.last_heartbeat = time.time()
            node.last_error = None
            node.can_accept_reads = bool(data.get("can_accept_reads", True))
            node.can_accept_writes = bool(data.get("can_accept_writes", True))
            node.failed_requests = 0

            if (
                node.avg_latency_ms >= self.config.unhealthy_latency_ms
                or node.disk_usage_percent >= self.config.unhealthy_disk_usage_percent
            ):
                node.health = HealthStatus.UNHEALTHY
                node.circuit_open = True
            elif (
                node.avg_latency_ms >= self.config.degraded_latency_ms
                or node.disk_usage_percent >= self.config.degraded_disk_usage_percent
                or data.get("status") == "DEGRADED"
            ):
                node.health = HealthStatus.DEGRADED
                node.circuit_open = False
            else:
                node.health = HealthStatus.HEALTHY
                node.circuit_open = False

        except Exception as exc:
            node.health = HealthStatus.UNHEALTHY
            node.last_error = str(exc)
            node.circuit_open = True

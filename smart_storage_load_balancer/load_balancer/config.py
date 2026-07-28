
from pathlib import Path
from typing import Any, Dict
import yaml
from .models import NodeConfig

# Default path to the YAML file that stores cluster, replication, consistent hashing, health-check, and node configuration.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "nodes.yaml"

class AppConfig:
    def __init__(self, raw: Dict[str, Any]):
        # Keep the original raw configuration for debugging or future use.
        self.raw = raw

        # Replication and quorum settings.
        self.replication_factor = int(raw.get("replication", {}).get("factor", 3))
        self.write_quorum = int(raw.get("replication", {}).get("write_quorum", 2))
        self.read_quorum = int(raw.get("replication", {}).get("read_quorum", 1))

         # Consistent hashing settings.
        self.virtual_nodes = int(raw.get("consistent_hash", {}).get("virtual_nodes", 100))

        # Health-check thresholds used to classify nodes as healthy, degraded, or unhealthy.
        health = raw.get("health", {})
        self.health_check_interval_seconds = float(health.get("check_interval_seconds", 2))
        self.health_timeout_seconds = float(health.get("timeout_seconds", 1.5))
        self.degraded_latency_ms = float(health.get("degraded_latency_ms", 150))
        self.unhealthy_latency_ms = float(health.get("unhealthy_latency_ms", 500))
        self.degraded_disk_usage_percent = float(health.get("degraded_disk_usage_percent", 85))
        self.unhealthy_disk_usage_percent = float(health.get("unhealthy_disk_usage_percent", 95))

        # Convert each node entry from YAML into a validated NodeConfig object.
        self.nodes = [NodeConfig(**node) for node in raw.get("nodes", [])]

def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Read the YAML configuration file and return an AppConfig object."""
    with open(path, "r", encoding="utf-8") as f:
        # yaml.safe_load safely parses YAML into a Python dictionary.
        return AppConfig(yaml.safe_load(f))

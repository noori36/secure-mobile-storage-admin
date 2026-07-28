
import bisect
import hashlib
from typing import Dict, Iterable, List

class ConsistentHashRing:
    """
    Consistent hashing maps an object key to one or more storage nodes.
    Adding/removing a node only remaps part of the key space.
    """

    def __init__(self, node_ids: Iterable[str], virtual_nodes: int = 100):
        # Number of virtual positions each physical node gets on the hash ring.
        self.virtual_nodes = virtual_nodes

        # Maps hash-ring positions to physical node IDs.
        self.ring: Dict[int, str] = {}

        # Sorted list of hash positions for fast lookup using binary search.
        self.sorted_keys: List[int] = []

        # Add all configured storage nodes to the ring.
        for node_id in node_ids:
            self.add_node(node_id)

    @staticmethod
    def _hash(value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return int(digest, 16)

    def add_node(self, node_id: str):
        if node_id in set(self.ring.values()):
            return
        for i in range(self.virtual_nodes):
            key = self._hash(f"{node_id}:vnode:{i}")
            self.ring[key] = node_id
            bisect.insort(self.sorted_keys, key)

    def remove_node(self, node_id: str):
        keys_to_remove = [key for key, value in self.ring.items() if value == node_id]
        for key in keys_to_remove:
            del self.ring[key]
            index = bisect.bisect_left(self.sorted_keys, key)
            if index < len(self.sorted_keys) and self.sorted_keys[index] == key:
                self.sorted_keys.pop(index)

    def get_replicas(self, object_key: str, replication_factor: int) -> List[str]:
        if not self.sorted_keys:
            return []
        start_hash = self._hash(object_key)
        index = bisect.bisect_left(self.sorted_keys, start_hash)
        replicas: List[str] = []
        visited = 0
        while len(replicas) < replication_factor and visited < len(self.sorted_keys):
            ring_key = self.sorted_keys[(index + visited) % len(self.sorted_keys)]
            node_id = self.ring[ring_key]
            if node_id not in replicas:
                replicas.append(node_id)
            visited += 1
        return replicas

    def snapshot(self):
        return {
            "virtual_nodes": self.virtual_nodes,
            "ring_size": len(self.sorted_keys),
            "physical_nodes": sorted(set(self.ring.values())),
        }

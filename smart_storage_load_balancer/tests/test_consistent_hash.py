
from load_balancer.consistent_hash import ConsistentHashRing

def test_consistent_hash_returns_unique_replicas():
    ring = ConsistentHashRing(["a", "b", "c", "d"], virtual_nodes=10)
    replicas = ring.get_replicas("file-1", 3)
    assert len(replicas) == 3
    assert len(set(replicas)) == 3

def test_consistent_hash_is_stable_for_same_key():
    ring = ConsistentHashRing(["a", "b", "c", "d"], virtual_nodes=10)
    assert ring.get_replicas("file-1", 3) == ring.get_replicas("file-1", 3)


from load_balancer.models import HealthStatus, NodeState
from load_balancer.scoring import calculate_score

def test_healthy_low_latency_node_scores_better_than_degraded_high_latency_node():
    good = NodeState(
        id="good",
        url="http://good",
        health=HealthStatus.HEALTHY,
        current_load=10,
        avg_latency_ms=10,
        queue_depth=1,
        disk_usage_percent=10,
    )

    bad = NodeState(
        id="bad",
        url="http://bad",
        health=HealthStatus.DEGRADED,
        current_load=80,
        avg_latency_ms=300,
        queue_depth=20,
        disk_usage_percent=90,
    )

    assert calculate_score(good, "READ") < calculate_score(bad, "READ")
    assert calculate_score(good, "WRITE") < calculate_score(bad, "WRITE")


import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def start_service(name, env, module, port):
    merged_env = os.environ.copy()
    merged_env.update(env)
    cmd = [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)]
    print(f"Starting {name} on port {port}...")
    return subprocess.Popen(cmd, cwd=ROOT, env=merged_env)

def main():
    processes = []
    node_configs = [
        ("node-a", 8001, 20, 0.01),
        ("node-b", 8002, 30, 0.02),
        ("node-c", 8003, 45, 0.03),
        ("node-d", 8004, 15, 0.01),
    ]
    try:
        for node_id, port, latency, failure_rate in node_configs:
            processes.append(start_service(
                name=node_id,
                env={
                    "NODE_ID": node_id,
                    "NODE_PORT": str(port),
                    "BASE_LATENCY_MS": str(latency),
                    "FAILURE_RATE": str(failure_rate),
                },
                module="storage_node.main:app",
                port=port,
            ))
        time.sleep(2)
        processes.append(start_service(
            name="load-balancer",
            env={},
            module="load_balancer.main:app",
            port=8010,
        ))

        print("\nAll services started.")
        print("Load balancer: http://127.0.0.1:8010")
        print("Swagger UI:    http://127.0.0.1:8010/docs")
        print("\nPress Ctrl+C to stop all services.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping services...")
        for p in processes:
            p.send_signal(signal.SIGTERM)
        for p in processes:
            p.wait(timeout=5)
        print("Stopped.")

if __name__ == "__main__":
    main()

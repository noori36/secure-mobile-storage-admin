
import json
import time
import requests

LB = "http://127.0.0.1:8000"

def pretty(title, response):
    print(f"\n--- {title} ---")
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)

def main():
    print("Checking cluster...")
    pretty("Health", requests.get(f"{LB}/health"))
    pretty("Nodes", requests.get(f"{LB}/nodes"))

    for i in range(1, 6):
        payload = {
            "object_id": f"file-{i}",
            "payload": f"hello from object {i}",
            "size_mb": i,
            "priority": "normal",
        }
        r = requests.post(f"{LB}/object", json=payload)
        pretty(f"Write file-{i}", r)
        time.sleep(0.2)

    for i in range(1, 6):
        r = requests.get(f"{LB}/object/file-{i}")
        pretty(f"Read file-{i}", r)
        time.sleep(0.2)

    pretty("Placement file-1", requests.get(f"{LB}/placement/file-1"))
    pretty("Metrics", requests.get(f"{LB}/metrics"))

    print("\nDisabling node-a from load balancer...")
    pretty("Disable node-a", requests.post(f"{LB}/admin/nodes/node-a/disable"))

    print("\nReading file-1 after node-a disable. It should fail over to another replica if needed.")
    pretty("Read file-1 after disable", requests.get(f"{LB}/object/file-1"))

    print("\nRe-enabling node-a...")
    pretty("Enable node-a", requests.post(f"{LB}/admin/nodes/node-a/enable"))

if __name__ == "__main__":
    main()

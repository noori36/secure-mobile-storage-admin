
import concurrent.futures
import random
import statistics
import time
import requests

LB = "http://127.0.0.1:8000"
TOTAL_REQUESTS = 100
READ_RATIO = 0.7

def write_object(i):
    start = time.perf_counter()
    response = requests.post(
        f"{LB}/object",
        json={
            "object_id": f"load-file-{i}",
            "payload": f"payload-{i}",
            "size_mb": random.randint(1, 5),
            "priority": random.choice(["normal", "high", "low"]),
        },
        timeout=5,
    )
    latency = (time.perf_counter() - start) * 1000
    return response.status_code, latency

def read_object(i):
    object_id = f"load-file-{random.randint(0, max(i, 1))}"
    start = time.perf_counter()
    response = requests.get(f"{LB}/object/{object_id}", timeout=5)
    latency = (time.perf_counter() - start) * 1000
    return response.status_code, latency

def main():
    print("Preloading objects...")
    for i in range(20):
        write_object(i)

    results = []
    start_all = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(TOTAL_REQUESTS):
            if random.random() < READ_RATIO:
                futures.append(executor.submit(read_object, i))
            else:
                futures.append(executor.submit(write_object, i + 1000))

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    elapsed = time.perf_counter() - start_all
    statuses = [r[0] for r in results]
    latencies = [r[1] for r in results]
    successes = sum(1 for s in statuses if 200 <= s < 300)

    print("\nLoad test results")
    print("-----------------")
    print(f"Total requests: {TOTAL_REQUESTS}")
    print(f"Successful: {successes}")
    print(f"Failed: {TOTAL_REQUESTS - successes}")
    print(f"Success rate: {successes / TOTAL_REQUESTS:.2%}")
    print(f"Throughput: {TOTAL_REQUESTS / elapsed:.2f} req/sec")
    print(f"Average latency: {statistics.mean(latencies):.2f} ms")
    print(f"P95 latency: {statistics.quantiles(latencies, n=20)[18]:.2f} ms")

if __name__ == "__main__":
    main()

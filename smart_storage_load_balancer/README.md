
# Smart Storage Load Balancer PoC

A local, ready-to-run custom load balancer for distributed storage traffic.

## Features

- Storage-aware read/write routing
- Health monitoring
- Metrics-aware node scoring
- Fault tolerance and failover
- Replication with write quorum
- Consistent hashing
- Metadata-based reads
- Idempotent write protection
- No Docker required

## Architecture

```text
Client
  |
  v
Load Balancer :8000
  |
  +--> Storage Node A :8001
  +--> Storage Node B :8002
  +--> Storage Node C :8003
  +--> Storage Node D :8004
```

## Install

```bash
cd storage_load_balancer_poc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run all services locally

```bash
python scripts/run_all.py
```

This starts:

- Load balancer: http://127.0.0.1:8000
- Storage node A: http://127.0.0.1:8001
- Storage node B: http://127.0.0.1:8002
- Storage node C: http://127.0.0.1:8003
- Storage node D: http://127.0.0.1:8004

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Manual test commands

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Check nodes, health, load, latency, and scores:

```bash
curl http://127.0.0.1:8000/nodes
```

Write an object:

```bash
curl -X POST http://127.0.0.1:8000/object \
  -H "Content-Type: application/json" \
  -d '{"object_id":"file-1","payload":"hello distributed storage","size_mb":1,"priority":"normal"}'
```

Read the object:

```bash
curl http://127.0.0.1:8000/object/file-1
```

Check consistent-hash placement and actual metadata:

```bash
curl http://127.0.0.1:8000/placement/file-1
```

Disable a node from the load balancer:

```bash
curl -X POST http://127.0.0.1:8000/admin/nodes/node-a/disable
```

Enable the node again:

```bash
curl -X POST http://127.0.0.1:8000/admin/nodes/node-a/enable
```

Force storage node failure:

```bash
curl -X POST http://127.0.0.1:8001/admin/failure-mode \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

Disable failure mode:

```bash
curl -X POST http://127.0.0.1:8001/admin/failure-mode \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Run demo

```bash
python scripts/demo_client.py
```

## Run load test

```bash
python scripts/load_test.py
```

## Run unit tests

```bash
pytest tests
```

## How the write path works

1. Client sends `POST /object`.
2. Load balancer hashes the `object_id` using consistent hashing.
3. It selects preferred replica nodes.
4. It filters unhealthy nodes.
5. It scores candidate nodes using load, latency, queue depth, disk usage, and health.
6. It writes to multiple replicas.
7. The write succeeds if `write_quorum` acknowledgments are received.
8. Metadata is stored in memory.

## How the read path works

1. Client sends `GET /object/{object_id}`.
2. Load balancer checks object metadata.
3. It finds replica nodes.
4. It selects the best healthy replica.
5. If that replica fails, it retries another replica.

## Important PoC note

This project uses in-memory object storage and in-memory metadata. For production, replace metadata with Redis, etcd, PostgreSQL, or another persistent store.

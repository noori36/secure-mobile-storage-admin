from fastapi import FastAPI

app = FastAPI()

nodes = [
    {"id": "node-01", "status": "online", "disk_usage": 65, "latency": 120},
    {"id": "node-02", "status": "online", "disk_usage": 45, "latency": 98},
    {"id": "node-03", "status": "degraded", "disk_usage": 90, "latency": 250}
]

@app.get("/")
def home():
    return {"message": "Storage Admin API"}

@app.post("/login")
def login():
    return {"token": "insecure-admin-token"}

@app.get("/nodes")
def get_nodes():
    return nodes
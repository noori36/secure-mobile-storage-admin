from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class LoginRequest(BaseModel):
    username: str
    password: str


nodes = [
    {
        "id": "node-01",
        "status": "online",
        "disk_usage": 65,
        "latency": 120
    },
    {
        "id": "node-02",
        "status": "online",
        "disk_usage": 45,
        "latency": 98
    },
    {
        "id": "node-03",
        "status": "degraded",
        "disk_usage": 90,
        "latency": 250
    }
]


@app.get("/")
def home():
    return {
        "message": "Storage Admin API"
    }


@app.post("/login")
def login(request: LoginRequest):

    # Intentionally insecure credentials
    if (
        request.username == "admin"
        and request.password == "admin123"
    ):
        return {
            "access_token": "insecure-admin-token",
            "token_type": "bearer"
        }

    raise HTTPException(
        status_code=401,
        detail="Invalid username or password"
    )


@app.get("/nodes")
def get_nodes():
    return nodes
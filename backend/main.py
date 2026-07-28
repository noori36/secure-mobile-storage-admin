from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Mobile Storage Administration Backend")

LOAD_BALANCER_URL = "http://127.0.0.1:8010"


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/")
def home():
    return {
        "message": "Storage Admin API",
        "load_balancer_url": LOAD_BALANCER_URL
    }


@app.post("/login")
def login(request: LoginRequest):
    # Intentionally insecure Week 7 credentials
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


def convert_health_status(health: str) -> str:
    """
    Convert load-balancer health values into the simpler
    values expected by the Android dashboard.
    """

    health = health.upper()

    if health == "HEALTHY":
        return "online"

    if health in {"DEGRADED", "SUSPECT"}:
        return "degraded"

    if health == "DISABLED":
        return "disabled"

    return "offline"


@app.get("/nodes")
async def get_nodes():
    """
    Retrieve real node information from the Smart Load Balancer
    and convert it into the format expected by Android.
    """

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{LOAD_BALANCER_URL}/nodes"
            )

        response.raise_for_status()
        load_balancer_nodes = response.json()

        android_nodes = []

        for node in load_balancer_nodes:
            android_nodes.append({
                "id": node["id"],
                "status": convert_health_status(
                    node.get("health", "UNKNOWN")
                ),
                "disk_usage": round(
                    node.get("disk_usage_percent", 0)
                ),
                "latency": round(
                    node.get("avg_latency_ms", 0)
                ),
                "current_load": node.get(
                    "current_load",
                    0
                ),
                "queue_depth": node.get(
                    "queue_depth",
                    0
                ),
                "read_score": node.get(
                    "read_score",
                    0
                ),
                "write_score": node.get(
                    "write_score",
                    0
                )
            })

        return android_nodes

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Smart Load Balancer is not running"
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Smart Load Balancer request timed out"
        )

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Smart Load Balancer returned an error: "
                f"{error.response.status_code}"
            )
        )

@app.post("/nodes/{node_id}/disable")
async def disable_node(node_id: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{LOAD_BALANCER_URL}"
                f"/admin/nodes/{node_id}/disable"
            )

        response.raise_for_status()
        return response.json()

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Smart Load Balancer is not running"
        )

    except httpx.HTTPStatusError as error:
        detail = "Could not disable node"

        try:
            detail = error.response.json().get(
                "detail",
                detail
            )
        except ValueError:
            pass

        raise HTTPException(
            status_code=error.response.status_code,
            detail=detail
        )


@app.post("/nodes/{node_id}/enable")
async def enable_node(node_id: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{LOAD_BALANCER_URL}"
                f"/admin/nodes/{node_id}/enable"
            )

        response.raise_for_status()
        return response.json()

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Smart Load Balancer is not running"
        )

    except httpx.HTTPStatusError as error:
        detail = "Could not enable node"

        try:
            detail = error.response.json().get(
                "detail",
                detail
            )
        except ValueError:
            pass

        raise HTTPException(
            status_code=error.response.status_code,
            detail=detail
        )
        
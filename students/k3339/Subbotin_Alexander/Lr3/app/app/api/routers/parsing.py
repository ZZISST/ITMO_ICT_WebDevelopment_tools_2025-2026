import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.settings.config import settings
from app.tasks import parse_url

router = APIRouter(prefix="/parsing", tags=["Parsing"])


@router.post("/sync")
async def parse_sync(url: str = Query(..., description="URL to parse")):
    """Call the parser service synchronously and return the result."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{settings.PARSER_SERVICE_URL}/parse",
                params={"url": url},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Parser service unavailable: {e}")


@router.post("/async")
async def parse_async(url: str = Query(..., description="URL to parse")):
    """Queue a parsing task via Celery and return the task ID."""
    task = parse_url.delay(url)
    return {"task_id": task.id, "status": "queued"}


@router.get("/result/{task_id}")
async def get_parse_result(task_id: str):
    """Get the result of an async parsing task."""
    result = parse_url.AsyncResult(task_id)
    response = {"task_id": task_id, "status": result.status}
    if result.ready():
        response["result"] = result.get()
    return response

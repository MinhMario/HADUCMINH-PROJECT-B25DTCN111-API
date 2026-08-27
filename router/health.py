from datetime import datetime, timezone

from fastapi import APIRouter, status

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "success": True,
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

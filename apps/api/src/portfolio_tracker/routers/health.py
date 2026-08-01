from fastapi import APIRouter

from portfolio_tracker.schemas.auth import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}

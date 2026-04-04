from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.accounts import router as accounts_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.transfers import router as transfers_router
from app.api.v1.summaries import router as summaries_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(categories_router)
api_router.include_router(accounts_router)
api_router.include_router(transactions_router)
api_router.include_router(transfers_router)
api_router.include_router(summaries_router)
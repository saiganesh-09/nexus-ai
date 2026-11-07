from fastapi import APIRouter

from app.api.v1 import analytics, auth, chat, compare, health, models, requests, routing, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(requests.router)
api_router.include_router(chat.router)
api_router.include_router(models.router)
api_router.include_router(routing.router)
api_router.include_router(analytics.router)
api_router.include_router(compare.router)

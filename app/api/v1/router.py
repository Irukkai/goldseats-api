"""Aggregates every v1 route module.

Feature routers land here as milestones ship: films (M1), theatres and
showtimes (M2), recommendations (M5), chat (M7), feed (M8).
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)

from fastapi import APIRouter

from app.api.routes import academic, announcements, auth, classroom, health, system


api_router = APIRouter()
api_router.include_router(academic.router)
api_router.include_router(announcements.router)
api_router.include_router(auth.router)
api_router.include_router(classroom.router)
api_router.include_router(health.router)
api_router.include_router(system.router)

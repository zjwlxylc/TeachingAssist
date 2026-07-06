from fastapi import APIRouter

from app.api.routes import academic, ai, announcements, auth, classroom, health, homework, questions, system


api_router = APIRouter()
api_router.include_router(academic.router)
api_router.include_router(ai.router)
api_router.include_router(announcements.router)
api_router.include_router(auth.router)
api_router.include_router(classroom.router)
api_router.include_router(health.router)
api_router.include_router(homework.router)
api_router.include_router(questions.router)
api_router.include_router(system.router)

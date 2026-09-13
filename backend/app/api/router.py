from fastapi import APIRouter

from app.api.routes import (
    document_file,
    documents,
    health,
    investigate,
    investigations,
    project_documents,
    projects,
    search,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(document_file.router)
api_router.include_router(search.router)
api_router.include_router(investigate.router)
api_router.include_router(investigations.router)
api_router.include_router(projects.router)
api_router.include_router(project_documents.router)

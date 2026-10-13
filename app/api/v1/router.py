from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.members import router as members_router
from app.api.v1.endpoints.users import router as users_router
from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.services import router as services_router
from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.deployments import router as deployments_router
from app.api.v1.endpoints.dependencies import router as dependencies_router
from app.api.v1.endpoints.hypotheses import router as hypotheses_router
from app.api.v1.endpoints.evidence import router as evidence_router
from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.explanations import router as explanations_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(incidents_router)
api_router.include_router(services_router)
api_router.include_router(events_router)
api_router.include_router(deployments_router)
api_router.include_router(dependencies_router)
api_router.include_router(hypotheses_router)
api_router.include_router(evidence_router)
api_router.include_router(analysis_router)
api_router.include_router(explanations_router)


api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(members_router)
api_router.include_router(users_router)
from app.api.v1.endpoints.comments import router as comments_router
from app.api.v1.endpoints.labels import router as labels_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.attachments import router as attachments_router
from app.api.v1.endpoints.activity import router as activity_router

api_router.include_router(comments_router)

api_router.include_router(labels_router)

api_router.include_router(notifications_router)

api_router.include_router(attachments_router)

api_router.include_router(activity_router)

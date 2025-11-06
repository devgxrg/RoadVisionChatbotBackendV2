"""
API endpoints for the TenderIQ analysis submodule.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.modules.auth.services.auth_service import get_current_active_user
from app.modules.auth.db.schema import User
from ..services.orchestrator_service import AnalysisOrchestratorService

router = APIRouter()

@router.get("/{tender_id}")
async def get_analysis_stream(
    tender_id: UUID,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Initiates and streams the result of a tender analysis.

    This endpoint uses Server-Sent Events (SSE) to provide real-time updates.
    - If the analysis has never been run, it triggers a new background task.
    - If the analysis is already running, it streams the current progress.
    - If the analysis is complete, it streams the full result and closes.

    **SSE Event Schema:**

    The stream sends events in the format: `event: <event_name>` and `data: <JSON_payload>`.
    The `data` payload will be a JSON string representation of the `SSEEvent` model.

    **Possible Events:**

    1.  **`event: initial_state`**: Sent once upon connection. The `data` payload contains the full current state of the analysis.
        -   `field`: "full"
        -   `data`: `TenderAnalysis` model as a dictionary.

    2.  **`event: update`**: Sent whenever a piece of the analysis is completed.
        -   `field`: The name of the updated JSON field (e.g., "one_pager_json", "scope_of_work_json").
        -   `data`: The corresponding Pydantic schema (`OnePagerSchema`, `ScopeOfWorkSchema`, etc.).

    3.  **`event: status`**: Sent when the overall progress or status message changes.
        -   `field`: "status"
        -   `data`: `{"status": str, "progress": int, "message": str}`

    4.  **`event: error`**: Sent if an error occurs during the analysis.
        -   `field`: "error"
        -   `data`: `{"message": str}`

    5.  **`event: control`**: Sent to signal the end of the stream.
        -   `field`: "control"
        -   `data`: "close"

    """
    orchestrator = AnalysisOrchestratorService(db)
    return await orchestrator.stream_analysis(tender_id, current_user.id, request)

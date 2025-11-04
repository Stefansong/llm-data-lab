from fastapi import APIRouter, Depends, HTTPException

from ..api.dependencies import get_current_user_id, get_database
from ..schemas import AnalysisTaskCreate, AnalysisTaskRead
from ..services import task_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/tasks", response_model=list[AnalysisTaskRead])
async def list_tasks(
    db=Depends(get_database), user_id: int = Depends(get_current_user_id)
) -> list[AnalysisTaskRead]:
    return await task_service.list_tasks(db, user_id=user_id)


@router.post("/tasks", response_model=AnalysisTaskRead)
async def create_task(
    payload: AnalysisTaskCreate,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> AnalysisTaskRead:
    task = await task_service.create_task(db, payload, user_id=user_id)
    if task is None:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return task


@router.get("/tasks/{task_id}", response_model=AnalysisTaskRead)
async def get_task(
    task_id: int,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> AnalysisTaskRead:
    task = await task_service.get_task(db, task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

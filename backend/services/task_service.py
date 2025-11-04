from typing import Optional

from databases import Database
from sqlalchemy import func, update

from ..models.task import analysis_tasks
from ..schemas import AnalysisTaskCreate, AnalysisTaskRead


async def create_task(db: Database, payload: AnalysisTaskCreate, user_id: int) -> Optional[AnalysisTaskRead]:
    values = payload.model_dump()
    values["user_id"] = user_id
    task_id = await db.execute(analysis_tasks.insert().values(**values))
    row = await db.fetch_one(
        analysis_tasks.select().where(
            (analysis_tasks.c.id == task_id) & (analysis_tasks.c.user_id == user_id)
        )
    )
    return AnalysisTaskRead(**row) if row else None


async def update_task(
    db: Database,
    task_id: int,
    *,
    user_id: Optional[int] = None,
    generated_code: Optional[str] = None,
    execution_stdout: Optional[str] = None,
    execution_stderr: Optional[str] = None,
    status: Optional[str] = None,
    summary: Optional[str] = None,
) -> Optional[AnalysisTaskRead]:
    values = {
        key: value
        for key, value in {
            "generated_code": generated_code,
            "execution_stdout": execution_stdout,
            "execution_stderr": execution_stderr,
            "status": status,
            "summary": summary,
        }.items()
        if value is not None
    }
    base_query = analysis_tasks.select().where(analysis_tasks.c.id == task_id)
    if user_id is not None:
        base_query = base_query.where(analysis_tasks.c.user_id == user_id)

    if not values:
        row = await db.fetch_one(base_query)
        return AnalysisTaskRead(**row) if row else None

    update_query = (
        update(analysis_tasks)
        .where(analysis_tasks.c.id == task_id)
        .values(**values, updated_at=func.now())
        .returning(analysis_tasks)
    )
    if user_id is not None:
        update_query = update_query.where(analysis_tasks.c.user_id == user_id)

    row = await db.fetch_one(update_query)
    return AnalysisTaskRead(**row) if row else None


async def list_tasks(db: Database, user_id: int, limit: int = 20) -> list[AnalysisTaskRead]:
    query = (
        analysis_tasks.select()
        .where(analysis_tasks.c.user_id == user_id)
        .order_by(analysis_tasks.c.created_at.desc())
        .limit(limit)
    )
    rows = await db.fetch_all(query)
    return [AnalysisTaskRead(**row) for row in rows]


async def get_task(db: Database, task_id: int, user_id: int) -> Optional[AnalysisTaskRead]:
    row = await db.fetch_one(
        analysis_tasks.select().where(
            (analysis_tasks.c.id == task_id) & (analysis_tasks.c.user_id == user_id)
        )
    )
    if not row:
        return None
    return AnalysisTaskRead(**row)

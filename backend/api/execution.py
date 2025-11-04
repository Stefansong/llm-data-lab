from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..api.dependencies import get_current_user_id, get_database
from ..config import get_settings
from ..sandbox.runner import CodeExecutionError, run_python_code
from ..schemas import CodeExecutionRequest, CodeExecutionResult
from ..services import task_service

router = APIRouter(prefix="/analysis", tags=["analysis"])
settings = get_settings()


@router.post("/run", response_model=CodeExecutionResult)
async def run_analysis(
    payload: CodeExecutionRequest,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> CodeExecutionResult:
    async def _execute_and_persist():
        try:
            result = await run_python_code(
                payload.code,
                dataset_filename=payload.dataset_filename,
                task_id=payload.task_id,
                user_id=user_id,
            )
        except CodeExecutionError as exc:  # pragma: no cover - unexpected runtime err
            if payload.task_id:
                await task_service.update_task(
                    db,
                    payload.task_id,
                    user_id=user_id,
                    execution_stdout="",
                    execution_stderr=str(exc),
                    status="failed",
                )
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if payload.task_id:
            await task_service.update_task(
                db,
                payload.task_id,
                user_id=user_id,
                execution_stdout=result["stdout"],
                execution_stderr=result["stderr"],
                status="succeeded" if result["returncode"] == 0 else "failed",
            )
        return result

    result = await _execute_and_persist()
    return CodeExecutionResult(
        stdout=result["stdout"],
        stderr=result.get("stderr") or None,
        status="succeeded" if result["returncode"] == 0 else "failed",
        artifacts=result.get("artifacts", []),
    )


@router.get("/artifacts/{artifact_folder}/{filename}")
async def get_artifact(artifact_folder: str, filename: str):
    base_path = settings.artifacts_dir.resolve()
    target = (base_path / artifact_folder / filename).resolve()
    if base_path not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target)

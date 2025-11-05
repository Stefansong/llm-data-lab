import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..api.dependencies import get_current_user_id, get_database
from ..config import get_settings
from ..sandbox.runner import CodeExecutionError, run_python_code
from ..schemas import CodeExecutionRequest, CodeExecutionResult
from ..services import task_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

# 🔒 用户并发执行跟踪（防止单用户占用所有资源）
_user_executions: dict[int, int] = {}
_execution_lock = asyncio.Lock()
MAX_CONCURRENT_EXECUTIONS_PER_USER = 2  # 每用户最多 2 个并发执行


@router.post("/run", response_model=CodeExecutionResult)
@limiter.limit("5/minute")  # 🔒 每分钟最多 5 次代码执行（防止滥用）
async def run_analysis(
    request: Request,
    payload: CodeExecutionRequest,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> CodeExecutionResult:
    """
    执行用户提交的 Python 代码。

    安全限制：
    - 速率限制：5 次/分钟（IP 级别）
    - 并发限制：每用户最多 2 个并发执行
    - 资源限制：在沙箱中应用（内存、CPU、超时）
    """

    # 🔒 检查用户并发执行数量
    async with _execution_lock:
        current_count = _user_executions.get(user_id, 0)
        if current_count >= MAX_CONCURRENT_EXECUTIONS_PER_USER:
            logger.warning(
                f"User {user_id} exceeded concurrent execution limit ({current_count}/{MAX_CONCURRENT_EXECUTIONS_PER_USER})"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Too many concurrent executions. Maximum {MAX_CONCURRENT_EXECUTIONS_PER_USER} allowed."
            )
        _user_executions[user_id] = current_count + 1

    logger.info(f"Code execution started for user {user_id} (task_id={payload.task_id})")

    try:
        async def _execute_and_persist():
            try:
                result = await run_python_code(
                    payload.code,
                    dataset_filename=payload.dataset_filename,
                    task_id=payload.task_id,
                    user_id=user_id,
                )
                logger.info(
                    f"Code execution completed for user {user_id}: "
                    f"returncode={result['returncode']}, artifacts={len(result.get('artifacts', []))}"
                )
            except CodeExecutionError as exc:
                logger.error(f"Code execution error for user {user_id}: {exc}")
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

    finally:
        # 🔒 释放并发槽位
        async with _execution_lock:
            _user_executions[user_id] = max(0, _user_executions.get(user_id, 1) - 1)
            if _user_executions[user_id] == 0:
                del _user_executions[user_id]


@router.get("/artifacts/{artifact_folder}/{filename}")
async def get_artifact(artifact_folder: str, filename: str):
    base_path = settings.artifacts_dir.resolve()
    target = (base_path / artifact_folder / filename).resolve()
    if base_path not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target)

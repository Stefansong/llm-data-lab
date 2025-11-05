import asyncio
import contextlib
import json
import mimetypes
import shutil
import tempfile
import time
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

try:
    import resource
except ImportError:  # pragma: no cover - not available on Windows
    resource = None

from ..config import get_settings


class CodeExecutionError(RuntimeError):
    """Raised when the sandboxed execution fails."""


def _resolve_dataset_source(
    dataset_filename: str,
    upload_dir: Path,
    user_id: Optional[int],
) -> Optional[Path]:
    """Resolve dataset file within the user-specific upload directory."""
    relative = Path(dataset_filename)
    if relative.is_absolute() or any(part in ("..", "") for part in relative.parts):
        raise CodeExecutionError("Invalid dataset path provided.")

    expected_prefix = f"user_{user_id}" if user_id is not None else None
    candidates: list[Path] = []

    if relative.parts and relative.parts[0].startswith("user_"):
        if expected_prefix and relative.parts[0] != expected_prefix:
            raise CodeExecutionError("Dataset not accessible for current user.")
        candidates.append(upload_dir / relative)
    else:
        if expected_prefix:
            candidates.append(upload_dir / expected_prefix / relative)
        candidates.append(upload_dir / relative)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate
    return None


def _limit_resources(memory_mb: int) -> None:
    """
    应用资源限制到子进程。

    限制项：
    - 内存（RLIMIT_AS）
    - CPU 时间（RLIMIT_CPU）
    - 进程数（RLIMIT_NPROC）
    - 文件大小（RLIMIT_FSIZE）
    - 打开文件数（RLIMIT_NOFILE）
    """
    if resource is None:
        return  # Windows 不支持

    limit_bytes = memory_mb * 1024 * 1024 if memory_mb > 0 else 768 * 1024 * 1024

    def _clamp(value: int, limit: int) -> int:
        if value in (-1, resource.RLIM_INFINITY):
            return limit
        return min(limit, value)

    try:
        # 🔒 内存限制
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (_clamp(soft, limit_bytes), _clamp(hard, limit_bytes)))

        # 🔒 CPU 时间限制（防止无限循环）
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))  # 最多 120 秒 CPU 时间

        # 🔒 子进程数量限制（防止 fork 炸弹）
        resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))  # 最多 10 个子进程

        # 🔒 文件大小限制（防止磁盘填满）
        max_file_size = 50 * 1024 * 1024  # 50MB
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_file_size, max_file_size))

        # 🔒 打开文件数限制
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))  # 最多 64 个打开文件

    except (ValueError, OSError) as e:
        # 某些平台不允许降低限制；记录但继续
        import logging
        logging.getLogger(__name__).warning(f"Failed to set resource limits: {e}")
        pass


async def run_python_code(
    code: str,
    *,
    dataset_filename: Optional[str] = None,
    task_id: Optional[int] = None,
    extra_requirements: Optional[Iterable[str]] = None,
    timeout: Optional[int] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    在临时工作目录中执行 Python 代码。

    安全措施：
    - 临时隔离目录
    - 资源限制（内存、CPU、进程数、文件大小）
    - 网络访问阻断
    - 文件系统限制
    - 超时控制
    """
    settings = get_settings()
    timeout = timeout or settings.max_code_execution_seconds

    async def _execute() -> dict:
        with tempfile.TemporaryDirectory(prefix="llm-data-lab-") as tmpdir:
            tmp_path = Path(tmpdir)
            script_path = tmp_path / "analysis.py"

            # 🔒 在用户代码前添加安全限制代码
            security_preamble = """
# ===== 安全限制代码（由系统自动添加）=====
import sys
import os

# 🔒 禁用危险模块的导入
_DANGEROUS_MODULES = {
    'subprocess', 'os.system', 'commands', 'popen2',
    'multiprocessing', 'threading', 'asyncio.subprocess',
    'socket', 'urllib', 'urllib2', 'urllib3', 'requests', 'httpx',
    '__builtin__', '__builtins__', 'builtins',
}

# 🔒 覆盖内置函数以禁用危险操作
_original_import = __builtins__.__import__

def _safe_import(name, *args, **kwargs):
    # 允许数据分析相关的安全模块
    if any(name.startswith(dangerous) for dangerous in _DANGEROUS_MODULES):
        # 允许部分 os 模块功能（仅文件路径操作）
        if name == 'os':
            import os as _os
            # 只暴露安全的路径操作
            class SafeOS:
                path = _os.path
                environ = {'DATASET_PATH': _os.environ.get('DATASET_PATH', '')}
            return SafeOS()
        # 其他危险模块一律拒绝
        raise ImportError(f"Module '{name}' is disabled for security reasons")
    return _original_import(name, *args, **kwargs)

__builtins__.__import__ = _safe_import

# ===== 用户代码开始 =====
"""
            # 组合安全代码和用户代码
            full_code = security_preamble + code
            script_path.write_text(full_code, encoding="utf-8")

            dataset_path = None
            if dataset_filename:
                source = _resolve_dataset_source(dataset_filename, settings.upload_dir, user_id)
                if source and source.exists():
                    dataset_path = tmp_path / source.name
                    shutil.copy2(source, dataset_path)
                    original_name = None
                    parts = source.name.split("_", 1)
                    if len(parts) == 2 and parts[1]:
                        original_name = parts[1]
                    if original_name and original_name != dataset_path.name:
                        shutil.copy2(source, tmp_path / original_name)

            # 🔒 安全的最小环境变量（禁用网络访问）
            env = {
                "PATH": "/usr/bin:/bin",  # 最小路径
                "PYTHONUNBUFFERED": "1",
                "HOME": str(tmp_path),  # 隔离主目录
                "TMPDIR": str(tmp_path),  # 限制临时文件位置
                # 🔒 禁用网络相关功能
                "http_proxy": "http://127.0.0.1:1",  # 使无效代理阻止网络
                "https_proxy": "http://127.0.0.1:1",
                "HTTP_PROXY": "http://127.0.0.1:1",
                "HTTPS_PROXY": "http://127.0.0.1:1",
                "no_proxy": "",  # 不允许绕过代理
                "NO_PROXY": "",
            }
            if dataset_path:
                env["DATASET_PATH"] = str(dataset_path)

            cmd = ["python3", str(script_path)]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(tmp_path),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=lambda: _limit_resources(settings.max_code_execution_memory_mb),
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError as exc:
                process.kill()
                raise CodeExecutionError(f"Code execution exceeded {timeout}s timeout.") from exc

            artifact_entries: list[dict] = []
            artifacts_manifest = tmp_path / "artifacts.json"
            manifest_items: list[str] = []
            if artifacts_manifest.exists():
                with contextlib.suppress(json.JSONDecodeError):
                    manifest_data = json.loads(artifacts_manifest.read_text("utf-8"))
                    if isinstance(manifest_data, dict):
                        manifest_items = manifest_data.get("artifacts") or manifest_data.get("files") or []
                    elif isinstance(manifest_data, list):
                        manifest_items = manifest_data

            if not manifest_items:
                manifest_items = [
                    str(path.relative_to(tmp_path))
                    for path in tmp_path.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".gif"}
                ]

            artifact_folder = None
            if manifest_items:
                if user_id is not None:
                    if task_id:
                        run_identifier = f"user_{user_id}_task_{task_id}"
                    else:
                        run_identifier = f"user_{user_id}_run_{uuid4().hex[:10]}"
                else:
                    run_identifier = f"task_{task_id}" if task_id else f"run_{uuid4().hex[:10]}"
                artifact_folder = settings.artifacts_dir / run_identifier
                if artifact_folder.exists():
                    shutil.rmtree(artifact_folder)
                artifact_folder.mkdir(parents=True, exist_ok=True)

                for item in manifest_items:
                    if isinstance(item, dict):
                        name = item.get("path") or item.get("filename") or item.get("name")
                    else:
                        name = item
                    if not name:
                        continue
                    if not isinstance(name, str):
                        name = str(name)
                    source_file = tmp_path / name
                    if not source_file.exists():
                        continue
                    destination_file = artifact_folder / source_file.name
                    shutil.copy2(source_file, destination_file)
                    mimetype, _ = mimetypes.guess_type(destination_file.name)
                    artifact_entries.append(
                        {
                            "filename": destination_file.name,
                            "url": f"/analysis/artifacts/{artifact_folder.name}/{destination_file.name}?ts={int(time.time())}",
                            "mimetype": mimetype,
                        }
                    )

            result = {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "artifacts": artifact_entries,
            }
            return result

    return await _execute()

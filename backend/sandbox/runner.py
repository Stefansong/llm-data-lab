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
    """Apply soft resource caps for the subprocess."""
    if memory_mb <= 0 or resource is None:
        return
    limit_bytes = memory_mb * 1024 * 1024
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)

    def _clamp(value: int) -> int:
        if value in (-1, resource.RLIM_INFINITY):
            return limit_bytes
        return min(limit_bytes, value)

    try:
        resource.setrlimit(resource.RLIMIT_AS, (_clamp(soft), _clamp(hard)))
    except (ValueError, OSError):
        # Some platforms disallow lowering limits; ignore and proceed.
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
    """Execute Python code inside a temporary working directory."""
    settings = get_settings()
    timeout = timeout or settings.max_code_execution_seconds

    async def _execute() -> dict:
        with tempfile.TemporaryDirectory(prefix="llm-data-lab-") as tmpdir:
            tmp_path = Path(tmpdir)
            script_path = tmp_path / "analysis.py"
            script_path.write_text(code, encoding="utf-8")

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

            env = {
                **dict(PATH=str(Path("/usr/bin")) + ":" + str(Path("/bin"))),
                **dict(PYTHONUNBUFFERED="1"),
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

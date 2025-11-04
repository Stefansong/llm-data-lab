from pathlib import Path
from typing import Optional
from uuid import uuid4

import openpyxl
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..api.dependencies import get_current_user_id
from ..config import get_settings

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _count_csv_rows(path: Path) -> Optional[int]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            total = sum(1 for _ in fh)
        # subtract header row if present (at least one row read)
        return max(total - 1, 0)
    except OSError:
        return None


def _count_excel_rows(path: Path) -> Optional[int]:
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        worksheet = workbook.active
        rows = max(worksheet.max_row - 1, 0)
        workbook.close()
        return rows
    except Exception:
        return None


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dataset must include a filename.")

    extension = Path(file.filename).suffix.lower().lstrip(".")
    if extension not in settings.allowed_upload_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    safe_name = f"{uuid4().hex}_{Path(file.filename).name}"
    user_dir = settings.upload_dir / f"user_{user_id}"
    user_dir.mkdir(parents=True, exist_ok=True)
    destination = user_dir / safe_name
    content = await file.read()
    destination.write_bytes(content)

    try:
        if extension == "csv":
            df = pd.read_csv(destination, nrows=500)
            total_rows = _count_csv_rows(destination)
        else:
            df = pd.read_excel(destination, nrows=500)
            total_rows = _count_excel_rows(destination)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse dataset: {exc}") from exc

    preview = df.head(20).to_dict(orient="records")
    schema_preview = {col: str(dtype) for col, dtype in df.dtypes.items()}
    row_count = total_rows if total_rows is not None else len(df)

    relative_name = destination.relative_to(settings.upload_dir)

    return {
        "filename": str(relative_name),
        "original_filename": file.filename,
        "columns": list(df.columns),
        "schema": schema_preview,
        "preview": preview,
        "rows": row_count,
    }

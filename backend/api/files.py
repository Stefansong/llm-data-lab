import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

import openpyxl
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pandas.errors import EmptyDataError, ParserError

from ..api.dependencies import get_current_user_id
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/datasets", tags=["datasets"])

# 🔒 文件签名（魔数）用于验证真实文件类型
FILE_SIGNATURES = {
    "csv": [
        b"",  # CSV 没有固定签名，允许空字节开头（将通过内容验证）
    ],
    "xlsx": [
        b"PK\x03\x04",  # ZIP 格式（XLSX 是 ZIP 压缩的 XML）
    ],
    "xls": [
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # Microsoft Office 旧格式 (OLE2)
    ],
}


def _validate_file_signature(file_bytes: bytes, extension: str) -> bool:
    """
    验证文件签名是否与扩展名匹配。

    Args:
        file_bytes: 文件的前几个字节
        extension: 文件扩展名

    Returns:
        True if valid, False otherwise
    """
    if extension not in FILE_SIGNATURES:
        return False

    # CSV 特殊处理：允许任何开头，但会在后续 pandas 解析时验证
    if extension == "csv":
        return True

    signatures = FILE_SIGNATURES[extension]
    return any(file_bytes.startswith(sig) for sig in signatures)


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
    """
    上传数据集文件（CSV, XLSX, XLS）。

    安全限制：
    - 文件大小限制（默认 10MB）
    - MIME 类型验证（文件签名检查）
    - 流式写入防止内存溢出
    - 用户隔离存储
    """
    settings = get_settings()

    # 1. 验证文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dataset must include a filename.")

    # 2. 验证扩展名
    extension = Path(file.filename).suffix.lower().lstrip(".")
    if extension not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_upload_extensions)}"
        )

    # 3. 准备存储路径
    safe_name = f"{uuid4().hex}_{Path(file.filename).name}"
    user_dir = settings.upload_dir / f"user_{user_id}"
    user_dir.mkdir(parents=True, exist_ok=True)
    destination = user_dir / safe_name

    # 4. 流式读取文件，检查大小和类型
    max_size = settings.max_upload_size_mb * 1024 * 1024  # 转换为字节
    total_size = 0
    first_chunk = None

    try:
        with destination.open("wb") as f:
            while chunk := await file.read(8192):  # 8KB 块
                # 4a. 检查文件大小
                total_size += len(chunk)
                if total_size > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                    )

                # 4b. 验证文件签名（仅第一块）
                if first_chunk is None:
                    first_chunk = chunk
                    if not _validate_file_signature(chunk, extension):
                        raise HTTPException(
                            status_code=400,
                            detail=f"File signature does not match extension .{extension}. Possible file type mismatch."
                        )

                # 4c. 写入文件
                f.write(chunk)

        logger.info(
            f"File uploaded: {file.filename} ({total_size} bytes) by user {user_id}"
        )

    except HTTPException:
        # 清理已写入的文件
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        # 清理并报告意外错误
        destination.unlink(missing_ok=True)
        logger.error(f"Upload failed for {file.filename}: {exc}")
        raise HTTPException(status_code=500, detail="File upload failed") from exc

    # 5. 解析和验证数据集
    try:
        if extension == "csv":
            df = pd.read_csv(destination, nrows=500)
            total_rows = _count_csv_rows(destination)
        else:  # xlsx, xls
            df = pd.read_excel(destination, nrows=500)
            total_rows = _count_excel_rows(destination)

    except ParserError as exc:
        destination.unlink(missing_ok=True)
        logger.warning(f"CSV parse error for {file.filename}: {exc}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV format: {str(exc)[:100]}"
        ) from exc
    except EmptyDataError:
        destination.unlink(missing_ok=True)
        logger.warning(f"Empty file uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="File is empty")
    except PermissionError as exc:
        destination.unlink(missing_ok=True)
        logger.error(f"Permission error for {file.filename}: {exc}")
        raise HTTPException(status_code=500, detail="File system permission error") from exc
    except Exception as exc:
        destination.unlink(missing_ok=True)
        logger.error(f"Failed to parse {file.filename}: {exc}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse dataset: {str(exc)[:100]}"
        ) from exc

    # 6. 生成预览和元数据
    preview = df.head(20).to_dict(orient="records")
    schema_preview = {col: str(dtype) for col, dtype in df.dtypes.items()}
    row_count = total_rows if total_rows is not None else len(df)
    relative_name = destination.relative_to(settings.upload_dir)

    logger.info(
        f"Dataset parsed successfully: {file.filename} ({row_count} rows, {len(df.columns)} columns)"
    )

    return {
        "filename": str(relative_name),
        "original_filename": file.filename,
        "columns": list(df.columns),
        "schema": schema_preview,
        "preview": preview,
        "rows": row_count,
    }

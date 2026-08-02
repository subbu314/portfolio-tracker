from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import csv_import
from portfolio_tracker.schemas.import_ import ImportBadErrorResponse, ImportCsvResponse

router = APIRouter(prefix="/import", tags=["import"])


def _bad_detail(message: str, errors: list[str] | None = None) -> dict:
    return {
        "message": message,
        "errors": errors or [],
        "action": csv_import.REIMPORT_ACTION,
    }


@router.post(
    "/csv",
    response_model=ImportCsvResponse,
    responses={400: {"model": ImportBadErrorResponse}},
)
async def import_csv_endpoint(
    session: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> dict:
    uploads: list[UploadFile] = []
    if files:
        uploads.extend(files)
    if file is not None:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail=_bad_detail("No CSV file provided"))

    use_batch = bool(files) or len(uploads) > 1
    if use_batch:
        decoded: list[tuple[str, str]] = []
        early: list[csv_import.FileImportErr] = []
        for upload in uploads:
            name = upload.filename or "upload.csv"
            raw = await upload.read()
            try:
                decoded.append((name, raw.decode("utf-8-sig")))
            except UnicodeDecodeError:
                early.append(
                    {
                        "filename": name,
                        "ok": False,
                        "code": "encoding",
                        "message": "File must be UTF-8 CSV",
                        "errors": [],
                        "action": csv_import.REIMPORT_ACTION,
                    }
                )
        batch = csv_import.import_csv_batch(session, decoded)
        if early:
            batch["files"] = [*early, *batch["files"]]
            batch["summary"]["rejected"] += len(early)
        return batch

    upload = uploads[0]
    raw = await upload.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=_bad_detail("File must be UTF-8 CSV")
        ) from exc
    try:
        return csv_import.import_csv(session, text)
    except csv_import.CsvFormatError as exc:
        raise HTTPException(status_code=400, detail=_bad_detail(str(exc))) from exc
    except csv_import.CsvParseError as exc:
        raise HTTPException(
            status_code=400, detail=_bad_detail(str(exc), exc.errors)
        ) from exc

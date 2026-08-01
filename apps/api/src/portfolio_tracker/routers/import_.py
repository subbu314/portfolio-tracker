from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import csv_import

router = APIRouter(prefix="/import", tags=["import"])


@router.post(
    "/csv",
    responses={400: {"description": "Invalid CSV format, encoding, or row data"}},
)
async def import_csv_endpoint(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_db)],
) -> csv_import.ImportResult:
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 CSV") from exc

    try:
        return csv_import.import_csv(session, text)
    except csv_import.CsvFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except csv_import.CsvParseError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "errors": exc.errors},
        ) from exc

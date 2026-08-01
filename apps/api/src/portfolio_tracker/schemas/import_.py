from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImportResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["console_tradebook"]
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportOkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    ok: Literal[True]
    format: Literal["console_tradebook"]
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportErrResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    ok: Literal[False]
    code: Literal["encoding", "csv_format", "csv_parse", "empty"]
    message: str
    errors: list[str]
    action: str


class BatchImportResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[FileImportOkResponse | FileImportErrResponse]
    summary: dict[str, int]


class ImportBadDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    errors: list[str] = Field(default_factory=list)
    action: str


class ImportBadErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: ImportBadDetail


ImportCsvResponse = ImportResultResponse | BatchImportResultResponse

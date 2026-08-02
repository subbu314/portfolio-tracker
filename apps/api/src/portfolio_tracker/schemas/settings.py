from pydantic import BaseModel, ConfigDict


class BenchmarkBody(BaseModel):
    benchmark_index: str


class CategoryBody(BaseModel):
    category: str


class BenchmarkItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    symbol: str
    instrument_type: str
    mf_category: str | None
    needs_category: bool
    benchmark_index: str
    source: str


class BenchmarkListResponse(BaseModel):
    items: list[BenchmarkItem]


class BenchmarkUpdateResponse(BaseModel):
    instrument_id: int
    benchmark_index: str
    source: str


class CategoryUpdateResponse(BaseModel):
    instrument_id: int
    mf_category: str | None


class CatalogsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mf_categories: list[str]
    benchmark_indexes: list[str]

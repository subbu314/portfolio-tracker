# Task 4 Report: Import Response Schemas

## Status

DONE

## Implementation

- Added strict Pydantic response models for single-file import, batch import, successful files, rejected files, and structured bad-request details.
- Added `ImportCsvResponse` union without changing existing CSV import JSON fields.
- Wired `POST /import/csv` to the response union.
- Documented HTTP 400 responses with `ImportBadDetail` while retaining dictionary `HTTPException.detail` payloads.

## TDD Evidence

### RED

Created `tests/test_openapi_import.py` before production changes and ran:

```text
uv run pytest tests/test_openapi_import.py -v
```

Result: `1 failed, 1 warning`; `ImportResultResponse` was absent from OpenAPI components.

### GREEN and Regression

```text
uv run pytest tests/test_openapi_import.py tests/test_csv_import.py tests/test_api_integration.py -v
```

Result: `25 passed, 1 warning`.

```text
uv run pytest -q
```

Result: `123 passed, 1 warning`.

Warning is existing Starlette TestClient deprecation for `httpx`.

## Self-Review

- Schema fields and literals match existing `TypedDict` contracts exactly.
- OpenAPI includes all five required component schemas.
- Focused route tests exercise both single-file and batch response validation.
- Unrelated untracked plan documents remained untouched.
- IDE diagnostics found no new errors; existing import endpoint cognitive-complexity warning remains outside task scope.

## Commit

`bb5c9ae feat(api): add CSV import OpenAPI response models`

## Concerns

None. Existing third-party deprecation and cognitive-complexity warnings are outside task scope.

## Fix

### Changes

- Added strict `ImportBadErrorResponse` envelope with `detail: ImportBadDetail`.
- Updated `POST /import/csv` HTTP 400 OpenAPI response to reference the envelope without changing runtime `HTTPException` behavior or JSON fields.
- Extended OpenAPI regression coverage to require both schemas and verify the route's 400 response references `ImportBadErrorResponse`.

### Covering tests

- `tests/test_openapi_import.py::test_openapi_includes_import_schemas` checks `ImportBadDetail` and `ImportBadErrorResponse` components and the exact 400 response `$ref`.
- Existing CSV import and API integration tests cover unchanged runtime behavior.

### Commands and output

```text
$ uv run pytest tests/test_openapi_import.py tests/test_csv_import.py tests/test_api_integration.py -v
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
collected 25 items

tests/test_openapi_import.py::test_openapi_includes_import_schemas PASSED
tests/test_csv_import.py::test_import_equity_tradebook_inserts_rows PASSED
tests/test_csv_import.py::test_reimport_is_idempotent PASSED
tests/test_csv_import.py::test_overlapping_reordered_imports_without_trade_ids_are_idempotent PASSED
tests/test_csv_import.py::test_unknown_format_rejected PASSED
tests/test_csv_import.py::test_headers_are_normalized_for_detection PASSED
tests/test_csv_import.py::test_mf_tradebook_import PASSED
tests/test_csv_import.py::test_unexpected_segment_is_imported_and_flagged PASSED
tests/test_csv_import.py::test_parse_error_writes_nothing PASSED
tests/test_csv_import.py::test_non_positive_trade_values_are_rejected_without_writes[quantity-0] PASSED
tests/test_csv_import.py::test_non_positive_trade_values_are_rejected_without_writes[quantity--1] PASSED
tests/test_csv_import.py::test_non_positive_trade_values_are_rejected_without_writes[price-0] PASSED
tests/test_csv_import.py::test_non_positive_trade_values_are_rejected_without_writes[price--1] PASSED
tests/test_csv_import.py::test_non_positive_trade_values_are_rejected_without_writes[fees--0.01] PASSED
tests/test_csv_import.py::test_eq_symbol_with_etf_name_is_classified_as_etf PASSED
tests/test_csv_import.py::test_csv_endpoint_imports_multipart_file PASSED
tests/test_csv_import.py::test_financial_year_label_uses_indian_fy PASSED
tests/test_csv_import.py::test_batch_import_accepts_multiple_files_and_skips_duplicates PASSED
tests/test_csv_import.py::test_batch_import_rejects_bad_file_keeps_good_files PASSED
tests/test_csv_import.py::test_import_route_multi_file_and_wrong_input_action PASSED
tests/test_api_integration.py::test_message_response_removed PASSED
tests/test_api_integration.py::test_import_then_overview PASSED
tests/test_api_integration.py::test_settings_routes_manage_benchmark_and_category_overrides PASSED
tests/test_api_integration.py::test_settings_reject_unknown_benchmark_name PASSED
tests/test_api_integration.py::test_portfolio_performance_route_returns_contributors PASSED

======================== 25 passed, 1 warning in 1.31s =========================
```

```text
$ uv run pytest -q
........................................................................ [ 58%]
...................................................                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/subrahmanian@backbase.com/repos/personal/portfolio-tracker/apps/api/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
123 passed, 1 warning in 2.88s
```

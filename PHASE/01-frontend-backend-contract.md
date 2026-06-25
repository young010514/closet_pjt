# Phase 01 Frontend Backend Contract

## Goal
Confirm the current frontend/backend contract for personal color analysis.

## Current Findings
- Request: `POST /api/personal-color/analyses/`
- Body: `multipart/form-data`
- File field: `image`
- Frontend uses `FormData.append('image', imageFile)`.
- Frontend does not manually set `Content-Type`, so the browser can set the multipart boundary.
- Success response fields match the current UI needs:
  - `id`
  - `result_type`
  - `result_label`
  - `result_subtype`
  - `confidence`
  - `summary`
  - `best_colors`
  - `avoid_colors`
  - `recommendations`
  - `analysis_metrics`
  - `provider_name`
  - `model_version`
  - `created_at`
- Supported result types remain:
  - `spring_warm`
  - `summer_cool`
  - `autumn_warm`
  - `winter_cool`

## Planned Files
- No frontend code changes for Phase 01.

## Internal Work
- Keep frontend behavior unchanged unless a contract mismatch is found.

## Completion Conditions
- Contract is documented.
- No frontend change is made in Phase 01.

## Verification Commands
- Not run by request.

## Actual Results
- Contract documented.
- No frontend files changed.

## Remaining Risks
- Later provider work must keep this response shape stable.

# Phase 02 Env and GMS Config

## Goal
Make Django GMS configuration simple and predictable without touching real `.env` files.

## Current Findings
- Django should load `closet/.env`, which is `BASE_DIR / ".env"`.
- Root `.env` should not be required for the Django backend.
- Real `.env` files must remain ignored.
- `GMS_API_KEY` is the only key name used; `GMS_KEY` is not used.
- `PHASE/` was ignored and needed to be tracked as a project artifact.

## Planned Files
- `.gitignore`
- `closet/closet/settings.py`
- `closet/.env.example`
- `PHASE/README.md`
- `PHASE/00-current-state.md`
- `PHASE/01-frontend-backend-contract.md`
- `PHASE/02-env-and-gms-config.md`

## Internal Work
- Use `python-dotenv` only.
- Remove the duplicate manual env parser.
- Load `closet/.env` with `override=True` so local `.env` values are not masked by stale process env values.
- Strip string GMS settings.
- Keep `closet/.env` ignored.
- Remove only the `PHASE/` ignore rule.

## Completion Conditions
- `closet/.env.example` documents required GMS keys with placeholders only.
- `settings.py` reads GMS settings from `closet/.env`.
- No real secret is printed or committed.
- Work stops before Phase 03.

## Verification Commands
- Not run by request.

## Actual Results
- Duplicate manual env parser removed.
- `load_dotenv(BASE_DIR / ".env", override=True)` is used.
- GMS default model is `gpt-5.4-nano`.
- `closet/.env.example` added with placeholder key.
- `PHASE/` is no longer ignored.

## Remaining Risks
- Django must be restarted after changing `closet/.env`.
- Provider implementation is intentionally not changed in Phase 02.

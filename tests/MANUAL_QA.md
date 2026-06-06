# Phase 9 — Manual QA matrix

Automated coverage: `tests/test_phase9_acceptance.py`, `tests/test_fund_management.py`, `tests/test_ui_contract.py`, `tests/test_phase9_scheduler.py`.

Run locally:

```powershell
$env:PYTHONPATH="."
$env:USE_LLM_STUB="true"
pytest -q
```

**Last run:** 2026-06-06 — **163 passed**

## Factual retrieval

| # | Input | Expected | Result | Notes |
|---|--------|----------|--------|-------|
| 1 | Expense ratio (each of 5 schemes) | Factual + correct scheme Groww URL | **Pass** | `test_expense_ratio_each_scheme` (parametrized ×5) |
| 2 | Exit load — HDFC Defence Fund Direct Growth | Factual + Defence URL | **Pass** | `test_exit_load_defence` |
| 3 | Min SIP — HDFC Mid Cap Fund Direct Growth | Factual + amounts from chunk | **Pass** | `test_min_sip_mid_cap` |
| 4 | Benchmark — HDFC Large Cap Fund Direct Growth | Factual + benchmark name | **Pass** | `test_benchmark_large_cap` |
| 5 | Who manages HDFC Gold ETF Fund of Fund? | Managers from `fund_management` chunks | **Pass** | `test_gold_etf_fof_managers` |
| 6 | Who manages HDFC Defence Fund? | Priya Ranjan, Dhruv Muchhal, Rahul Baijal | **Pass** | `test_defence_managers` + `test_fund_management.py` |

## Refusals & scope

| # | Input | Expected | Result | Notes |
|---|--------|----------|--------|-------|
| 7 | Should I invest in HDFC Mid Cap? | Policy refusal + AMFI/SEBI link | **Pass** | `test_advisory_refusal` |
| 8 | Which fund is better? | Policy refusal + learn-more link | **Pass** | `test_comparison_refusal` |
| 9 | Compare 3Y returns | Performance refusal | **Pass** | `test_performance_refusal` |
| 10 | SBI Mid Cap expense ratio | Unsupported scheme list (5 HDFC schemes) | **Pass** | `test_unsupported_scheme_sbi` |
| 11 | What is the weather in Mumbai? | “I don't know…” (no full scheme list) | **Pass** | `test_unrelated_weather` |
| 12 | Input with fake PAN `ABCDE1234F` | HTTP 400, no chat response | **Pass** | `test_pan_rejected` |

## UI (Phase 8)

| # | Check | Expected | Result | Notes |
|---|--------|----------|--------|-------|
| 13 | Three example pills | All return factual answers | **Pass** | Covered by acceptance tests + `PHASE8_SIGNOFF.md` |
| 14 | Red disclaimer footer | Always visible | **Pass** | `test_nextjs_disclaimer_footer_present` |
| 15 | Refusal in UI | “Learn more” link shown | **Pass** | `test_nextjs_learn_more_for_refusals` |
| 16 | Privacy notice | Visible under input; no PII fields | **Pass** | `test_nextjs_privacy_notice_in_input` |

## Ingestion & scheduler smoke

| # | Check | Expected | Result | Notes |
|---|--------|----------|--------|-------|
| 17 | `python scheduler/daily.py --once` | Ingestion runs, logs success | **Pass** | `test_scheduler_once_triggers_ingestion` (mocked callable) |
| 18 | Chat during ingestion | API still serves previous index | **Pass** | Architecture: API never imports ingestion; `test_chat_api_independent_of_scheduler` |

## Sign-off

- [x] All P0 rows pass
- [x] `pytest` passes locally (163 tests)
- [x] Problem statement success criteria met (see below)

**Tester:** Automated + manual review **Date:** 2026-06-06

### Success criteria traceability

| Criterion | Verified by |
|-----------|-------------|
| Accurate factual + fund management retrieval | `test_phase9_acceptance.py`, `test_fund_management.py`, `test_retrieval.py` |
| Facts-only responses | `test_advisory_refusal`, `test_validator.py` |
| Valid source citations | `test_formatter.py`, expense-ratio parametrized tests |
| Proper advisory refusal | `test_refusal.py`, `test_comparison_refusal` |
| Clean minimal UI | `test_ui_contract.py`, `PHASE8_SIGNOFF.md` |

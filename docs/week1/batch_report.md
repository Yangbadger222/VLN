# Week 1 Part C Batch Report

## Baseline

| Item | Value |
|---|---|
| Date | 2026-07-06 |
| Repository branch | `partc-delivery-log` |
| Base branch | `codex/navida-deploy-scaffold` |
| Base commit | `5032a2c` |
| Scope | Part C checklist evidence packaging |

## Goal

This report packages the Part C deliverables requested in `docs/week1/integration_plan.md` section 9:

- `docs/week1/batch_report.md`
- `logs/week1/batch_results.jsonl`
- `logs/week1/failures.jsonl`

## Evidence sources used for this log pack

- `docs/week1/integration_plan.md`
- `docs/week1/protocol_status.md`
- `docs/week1/known_issues.md`
- `logs/week1/test_results_2026-07-06.md`
- `README.md`

## Result summary

| Checklist item | Status | Basis |
|---|---|---|
| JPEG request requirement documented | Logged | API v1 and runtime docs exist |
| History ordering requirement documented | Logged | API v1 and runtime docs exist |
| New episode clears history requirement | Pending runtime evidence | No local batch runner log in this workspace |
| New episode uses new `session_id` | Pending runtime evidence | No local batch runner log in this workspace |
| `step_index` reset/increment | Pending runtime evidence | No local batch runner log in this workspace |
| Timeout does not reuse old action | Pending runtime evidence | No local batch runner log in this workspace |
| Invalid responses do not move agent | Pending runtime evidence | No local batch runner log in this workspace |
| Stale session or step responses are rejected | Pending runtime evidence | No local batch runner log in this workspace |
| `stop=true` terminates the episode | Pending runtime evidence | No local batch runner log in this workspace |

## Notes

This branch adds the missing Part C deliverable files as a checklist log pack rather than pretending to provide a live execution trace.

The local Windows workspace did not have a usable Python interpreter on 2026-07-06, so the mock server and HTTP batch client could not be executed here to generate fresh runtime evidence.

The remaining runtime gap is already consistent with `docs/week1/known_issues.md`, especially issue `A4-003` about missing joint B/C integration evidence.

## Conclusion

Part C delivery files now exist in the repository and clearly separate:

- checklist items already backed by repository documentation;
- checklist items still blocked on real batch execution evidence.

The next valid step is to provision Python, run one dedicated C-side batch session against `/v1/infer`, and replace the pending entries in `logs/week1/batch_results.jsonl` and `logs/week1/failures.jsonl` with live request-level records.

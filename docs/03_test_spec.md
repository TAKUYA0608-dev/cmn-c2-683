# Test Specification — CMN-C2-683

Structured Output & Constrained Decoding Reliability Q&A Agent (Cat 2).

## Test Strategy
- Coverage target: **80%+** (achieved 92%, `--cov=src --cov-fail-under=80`)
- Test types: Unit (pre/post + inner nodes + services) / Unit (Cat 2 graph wiring) / Integration / Proof-of-Boundary
- Advisory-only / read-only agent: no live decoding, no JSON repair, no tool execution — tests assert
  the agent stays advisory and every path emits an audit event + the mandatory DRAFT disclaimer.

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict | `State(AgentState)`, NotRequired primitives + JSON strings; no PII/credentials | ✅ PASS |
| TC-02 | Degraded/rejected path never crashes | empty / oversize / injection → degraded `SUCCESS + error_code` (injection → `INJECTION_REJECTED`, untrusted body discarded `validated_input="{}"`); `post_process` S-3/S-4 always run — never `status=ERROR` | ✅ PASS |
| TC-03 | No sk-/JWT/AKIA credential literal in `src/` | `gate-credential-scan`: 0 violations | ✅ PASS |
| TC-05 | S-4: no duplicate lifecycle events | only domain `emit_trace_event()` calls | ✅ PASS |
| TC-06 | S-2 `_security_gate_input()` not overridden | `@final`; only `_extra_*` extended (hook is a no-op — rejection handled in `execute()`) | ✅ PASS |
| TC-07 | S-3 `_security_gate_output()` not overridden | `@final`; may raise via `_extra_*` | ✅ PASS |
| TC-08 | `required_trust_level` enforced | VERIFIED_EXTERNAL on every FunctionNode subclass (pre/post/3 inner) | ✅ PASS (`check_trust_level.py`) |
| TC-09 | S-2 injection/oversize reach post via real `Graph().invoke()` | prompt-injection & oversize → `SUCCESS + error_code`, `PostProcessNode` in `node_history`, out-of-scope envelope + DRAFT disclaimer, no rejected body/canary in output | ✅ PASS |
| TC-11 | S-4: ≥1 domain `emit_trace_event()` per `execute()` | emitted on every path incl. inner skip guards (count-only) | ✅ PASS |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Expected Result | Result |
|-------|----------|----------------|--------|
| PB-1 | `emit_trace_event()` fires from `shared.utils.audit_logger` | no silent failures | ✅ (real SDK on CI) |
| PB-2 | Post-invoke State is primitives only | no Pydantic/dataclass | ✅ PASS |
| PB-4 | Import isolation — no Level 0 imports | AST scan: 0 violations | ✅ PASS |
| PB-6 | Invoke order S-1 → S-4 → S-2 → execute → S-3 → S-4 | order verified | ✅ (real SDK on CI; local stub env-diff) |
| PB-7 | HITL interrupt propagation (conditional) | SKIPPED — hitl not used | ✅ (conditional stub) |
| Composition | Cat 2 `GraphNode`-in-main wraps inner `BaseGraph` (cached) | gate-composition passes | ✅ (S-0 gate) |

## Business Logic Tests

| BL-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | Schema-selection plan | "how strict JSON Schema…" + enum constraint | reliability_plan.contract + citations + checklist | ✅ PASS |
| BL-02 | Tool-call reliability concern | "reliable function-calling arguments" | guidance includes tool_call_reliability | ✅ PASS |
| BL-03 | Constrained-decoding concern | "grammar constrained decoding vs prompt" | concern=constrained_decoding classified | ✅ PASS |
| BL-04 | Failure/repair concern | "repair invalid output" | concern=failure_handling retrieved | ✅ PASS |
| BL-05 | Out-of-scope | non-reliability question | `out_of_scope`, no citations | ✅ PASS |
| BL-06 | Empty input | "   " | degraded SUCCESS + `INPUT_REJECTED`, still audits + safe answer | ✅ PASS |
| BL-07 | Mandatory DRAFT disclaimer | any guidance | S-3 gate blocks output missing it | ✅ PASS |
| BL-08 | Credential redaction | pasted `sk-…` / `AKIA…` | never persists in State / echoed in output | ✅ PASS |
| BL-09 | Injection degrades (not ERROR) | "ignore all previous instructions…" | SUCCESS + `INJECTION_REJECTED`, body discarded (`validated_input="{}"`), out-of-scope safe answer, audits; verified via real `Graph().invoke()` | ✅ PASS |
| BL-10 | Oversize degrades | > 20 000 chars | SUCCESS + `INPUT_TOO_LONG`, body discarded, out-of-scope safe answer, audits; verified via real `Graph().invoke()` | ✅ PASS |

## Test Execution Summary
- Collected 47 in `tests/unit` + `tests/integration` locally (incl. the real `Graph().invoke()`
  rejection acceptance tests for injection + oversize)
- Pass: **46** · Skip: **1** (server import — local stub env-diff) · env-diff: PB invoke-order / PB-7 (real SDK on CI)
- Coverage: **92%** (`--cov=src`, `--cov-fail-under=80`); ruff clean on `src/`

# Template Design Specification — CMN-C2-683

Structured Output & Constrained Decoding Reliability Q&A Agent (Cat 2).

## Position in AgentCore Architecture

- **Agent Class**: `StructuredOutputConstrainedDecodingReliabilityAgent` (module-level alias of `Graph`)
- **L1 Base**: **AgentBaseGraph** (Cat 2 — outer 5-node backbone; direct L1 inheritance, no L2)
- **Category**: Cat 2 — a multi-step advisory workflow (validate → intent-classify → versioned-KB
  retrieve → guidance-synthesize → safety/citation gate) producing a cited **Structured-Output
  Reliability Plan**; CMN industry (AI engineering infrastructure). `DocGenerationAgent` is a §5/§10
  pattern reference only.
- **Three-Layer Separation**: State = flat TypedDict; Node = L1 inheritance (`execute` override only);
  Graph = outer `AgentBaseGraph` + **`GraphNode` in the `main` slot** wrapping an inner `BaseGraph`

## Architecture Overview

Cat 2 pattern — the `main` slot is a **`GraphNode`** (`ReliabilityAdvisoryWorkflowGraphNode`, **subgraph
cached**) that wraps the inner `ReliabilityAdvisoryWorkflow` (`BaseGraph`). Inner graph is a **static
linear backbone with per-node skip guards**. **Advisory-only / read-only: the agent never decodes or
repairs JSON, never executes a tool-call, and never mutates a production schema, prompt, or config —
output is a DRAFT cited recommendation for human adoption.**

### Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | schema_version, session_id, trust_level | user_input | (framework) | InitializeNode (default) |
| pre_process | `PreProcessNode` (InputValidate) — S-1/S-2, non-executable/non-confidential check, credential redaction, question/constraint slots | user_input | validated_input, input_format, enriched_context | FunctionNode.execute |
| main | `ReliabilityAdvisoryWorkflowGraphNode` (GraphNode) → inner workflow | validated_input | result, retrieval_hit_count | GraphNode |
| post_process | `PostProcessNode` (SafetyAndCitationGate) — S-3 sanitize + citation completeness + reject unsupported claims + advisory disclaimer + S-4 audit | result | formatted_output, disclaimer, audit_logged | FunctionNode.execute |
| finalize | response_metadata, total_time_ms | | (framework) | FinalizeNode (default) |

**Inner workflow (`ReliabilityAdvisoryWorkflow` : BaseGraph):**

```
START → intent_classify → kb_retrieve → guidance_synthesize → END
```

| Inner node | Responsibility |
|---|---|
| IntentClassify | classify the technical question into one/more concerns: schema selection / validation placement / repair boundary / tool-call argument reliability / escalation |
| KbRetrieve (VersionedKBRetrieve) | deterministic retrieval over the **versioned** structured-output / constrained-decoding technical KB; 0-hit → out-of-scope safe answer |
| GuidanceSynthesize | compose a multi-part **Structured-Output Reliability Plan** (contract selection + validation placement + failure/repair handling + tool-call reliability + escalation) **conditioned on the retrieved evidence** (not a static lookup table) with source citations + a verification checklist |

### Data Flow

```
START → initialize → pre_process → main(GraphNode → inner linear workflow) → post_process → finalize → END
                                     ↓ (retry, max 3)
                                   pre_process
```

Rejected / 0-hit input sets `error_code` + `retrieval_hit_count=0`; `guidance_synthesize` emits the
out-of-scope safe answer — no fabricated, ungrounded reliability guidance.

**Degraded (S-2 rejection) flow — coherent execute-level handling.** Prompt-injection and oversize are
handled entirely in `pre_process.execute()` as a degraded **`status=SUCCESS + error_code`** path, NOT
as a `status=ERROR` hard reject. The untrusted body is discarded (`validated_input="{}"`,
`error_code=INJECTION_REJECTED` / `INPUT_TOO_LONG`); with the body discarded the inner workflow
naturally reaches 0-hit, `guidance_synthesize` returns the out-of-scope safe answer, and **post_process
(S-3 credential redaction + mandatory DRAFT disclaimer + S-4 terminal audit) always runs**. A
`status=ERROR` from the S-2 hook would short-circuit `__call__`, so the framework `route()` would send
the request straight to `finalize` and main / post_process would never run. The S-2
`_extra_security_gate_input()` hook is therefore a **no-op** (never raises, never sets `status=ERROR`);
all rejection logic lives in `execute()`. Both rejection cases are verified through a real
`Graph().invoke()` acceptance test (SUCCESS, PostProcessNode in `node_history`, out-of-scope envelope,
DRAFT disclaimer, no rejected body/canary in output). Classification and retrieval are **deterministic**
(keyword/concern scoring — no LLM in the rejection or retrieval path).

### State Definition

| Field | Type | Purpose |
|-------|------|---------|
| validated_input | str (JSON) | `{question, declared_constraints, current_setup}` (non-executable, non-confidential) |
| intent | str (JSON) | `{primary_intent, concerns[], constraints{}}` |
| retrieved_evidence / retrieval_hit_count | str/int | versioned-KB matches / 0 → out-of-scope safe answer |
| reliability_plan | str (JSON) | `{contract, validation_placement, failure_handling, tool_call_reliability, escalation, ...}` |
| result / formatted_output | str (JSON) | inner report / final envelope |
| disclaimer / audit_logged | str/bool | mandatory advisory (DRAFT) disclaimer + terminal audit |
| error_code / error_message | str | degraded path (SUCCESS + error_code, never status=ERROR) |

**State Constraints:** flat TypedDict; JSON strings for complex fields; **no PII / no credentials**
(any inadvertently supplied credential is redacted at pre_process); `enriched_context` is a JSON string
(ADR-005).

## Framework Utilization

- [x] **GraphNode-in-main** (Cat 2 composition, criterion #9) — `error_strategy="propagate"`, `propagate_hitl=False`, **subgraph cached** (`self._subgraph`)
- [x] S-1 `required_trust_level=VERIFIED_EXTERNAL` on every FunctionNode subclass (pre / post / all inner nodes)
- [x] S-2 `_extra_security_gate_input()` (pre) — **no hard reject**: a no-op that returns state unchanged and never raises (SDK 1.0.0); framework default PII masking still applies. Size cap + injection markers + non-executable/non-confidential handling are done in `execute()` as the degraded **`SUCCESS + error_code`** path (untrusted body discarded, `validated_input="{}"`), **never `status=ERROR`** — an ERROR short-circuits `__call__` and skips main / post_process / S-3 / S-4
- [x] S-3 `_extra_security_gate_output()` (post) — mandatory advisory-disclaimer preservation; **may raise** (SDK 1.0.0)
- [x] S-4 `emit_trace_event()` in every `execute()` (intent / topic counts / citation completeness only — no PII, no credentials); terminal audit always fires — including the inner skip guards (count-only domain event on the rejected / 0-hit branch)

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs; extend via `_extra_*` hooks only (S-2 hook is a no-op — rejection is a degraded `SUCCESS + error_code` inside `execute()`)
> - `GraphNode` (`ReliabilityAdvisoryWorkflowGraphNode`) → deliberate no-op (the inner FunctionNode gates apply)

## Import Isolation Confirmation
- [x] No `agenticstar` SDK (Level 0) import — PB-4
- [x] Import targets: `framework/`, `langgraph`, and `src.` only

## Design Decision Record

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| L1 base type | AgentBaseGraph | Fixed 5-slot pipeline, no autonomous loop |
| Composition | **GraphNode-in-main + inner BaseGraph (cached)** | Cat 2 multi-step advisory workflow |
| Inner topology | **Linear + per-node skip guards** | Conditional edges don't propagate across the subgraph boundary |
| Guidance synthesis | **Grounded in retrieved evidence (not a static `(strictness, model)` lookup table)** | §2-4 make-or-break: keeps Agent value (KB grounding + multi-part deliverable) distinct from a Tool |
| Live execution | **None — advisory-only / read-only** | Never decodes/repairs JSON, never runs a tool-call, never mutates prod schema/prompt/config; output is a DRAFT cited recommendation |
| Rejection signalling | SUCCESS + error_code | Guarantees post_process S-3/S-4 always run (SDK 1.0.0; ERROR would skip them) |

## Open Items (Stage ③ implementation MR)
- Node implementations (pre / post / intent_classify / kb_retrieve / guidance_synthesize) + inner workflow graph — shipped in the implementation MR.
- Seeded, versioned `ReliabilityKB` (structured-output / constrained-decoding guidance: JSON Schema, grammar-constrained decoding, function-calling reliability, validation placement, repair boundary, escalation) with provenance/source per record.
- `graph.py` module-level alias `StructuredOutputConstrainedDecodingReliabilityAgent = Graph` + `src/graph/__init__.py` export.
- Unit + integration + PB tests; coverage ≥ 89%.

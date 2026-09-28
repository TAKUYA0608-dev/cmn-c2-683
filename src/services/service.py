"""CMN-C2-683 — deterministic domain services (no framework imports).

``ReliabilityKB``: a seeded, **versioned** knowledge base of structured-output & constrained-decoding
reliability guidance (JSON Schema constraints, grammar-constrained decoding, function-calling argument
reliability, output-validation placement, repair boundary, escalation). Records are sourced from public
technical guidance and carry an explicit ``source`` + ``version`` per record.

Intent classification and retrieval are **deterministic** (keyword/tag scoring + concern matching) and
auditable. The template contains no live decoding, no JSON repair, and no tool execution — it is an
advisory Q&A KB. No PII / no credentials are stored.
"""

from __future__ import annotations

from typing import Any

# ── concern vocabulary (the technical decision the developer is asking about) ─────────────────────
_CONCERN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "schema_selection": (
        "schema",
        "json schema",
        "strict",
        "structured output",
        "response format",
        "field",
        "required",
        "enum",
        "type",
        "constrain the output",
        "output format",
        "additionalproperties",
    ),
    "constrained_decoding": (
        "constrained decoding",
        "grammar",
        "gbnf",
        "guided",
        "logit",
        "token mask",
        "regex decode",
        "guided decoding",
        "constrained generation",
        "state machine",
    ),
    "validation_placement": (
        "validate",
        "validation",
        "pydantic",
        "parse",
        "where to validate",
        "verify output",
        "post-validate",
        "boundary check",
        "reject",
        "schema validation",
    ),
    "failure_handling": (
        "invalid",
        "partial",
        "repair",
        "retry",
        "malformed",
        "truncated",
        "incomplete",
        "fix",
        "fallback",
        "self-heal",
        "reprompt",
        "recover",
    ),
    "tool_call_reliability": (
        "tool call",
        "tool-call",
        "function call",
        "function-calling",
        "tool argument",
        "arguments",
        "tool use",
        "parameters",
        "call signature",
        "unsafe execution",
    ),
    "escalation": (
        "escalate",
        "escalation",
        "human",
        "review",
        "approve",
        "approval",
        "confidence",
        "uncertain",
        "hitl",
        "human-in-the-loop",
        "when to stop",
    ),
}

# ── seeded, versioned reliability KB (public technical guidance) ───────────────────────────────────
# Each record: {topic_id, title, concern, contract_type, tags, source, version, recommendation,
#               verification_checks[]}
KB: list[dict[str, Any]] = [
    {
        "topic_id": "SO-SCHEMA-001",
        "title": "JSON Schema strict-mode contract selection",
        "concern": "schema_selection",
        "contract_type": "json_schema",
        "tags": [
            "schema",
            "json schema",
            "strict",
            "structured output",
            "response format",
            "required",
            "additionalproperties",
            "field",
        ],
        "source": "OpenAI Structured Outputs guide + JSON Schema 2020-12",
        "version": "2024-08",
        "recommendation": (
            "Prefer a strict JSON Schema (all fields required, additionalProperties=false) over a free-form "
            "'return JSON' prompt. Model the closed set of outputs explicitly; use nullable unions rather than "
            "optional keys so the contract is total."
        ),
        "verification_checks": [
            "additionalProperties is false on every object",
            "every property appears in `required` (use null unions for optionality)",
            "no unbounded free-text field carries control decisions",
        ],
    },
    {
        "topic_id": "SO-ENUM-002",
        "title": "Enum & bounded-field constraints",
        "concern": "schema_selection",
        "contract_type": "json_schema",
        "tags": ["enum", "bounded", "type", "field", "constrain the output", "schema", "categorical"],
        "source": "JSON Schema 2020-12 (enum/const, min/max)",
        "version": "2020-12",
        "recommendation": (
            "Encode every categorical output as an `enum` and every numeric output with min/max bounds so the "
            "decoder cannot emit an out-of-domain value. Avoid stringly-typed status fields."
        ),
        "verification_checks": [
            "categorical fields use `enum`, not free string",
            "numeric fields carry minimum/maximum",
            "a fuzz set of adversarial inputs never yields an out-of-enum value",
        ],
    },
    {
        "topic_id": "SO-DECODE-003",
        "title": "Grammar-constrained decoding vs prompt-only",
        "concern": "constrained_decoding",
        "contract_type": "grammar",
        "tags": [
            "constrained decoding",
            "grammar",
            "gbnf",
            "guided decoding",
            "logit",
            "token mask",
            "constrained generation",
        ],
        "source": "Guidance / Outlines / llama.cpp GBNF references",
        "version": "2024-06",
        "recommendation": (
            "For high-stakes contracts, back the JSON Schema with grammar-/token-level constrained decoding "
            "(GBNF, guided decoding, logit masking) so malformed JSON is structurally impossible, rather than "
            "relying on prompt instructions the model may ignore under distribution shift."
        ),
        "verification_checks": [
            "decoder enforces the grammar at token level, not just via prompt",
            "grammar is generated from the same schema that validation uses (single source of truth)",
            "measured malformed-output rate is ~0 on a regression set",
        ],
    },
    {
        "topic_id": "SO-VALID-004",
        "title": "Output validation placement (boundary re-validation)",
        "concern": "validation_placement",
        "contract_type": "validation",
        "tags": [
            "validate",
            "validation",
            "pydantic",
            "parse",
            "where to validate",
            "schema validation",
            "boundary check",
            "reject",
        ],
        "source": "Defensive-parsing / boundary-validation practice",
        "version": "2024",
        "recommendation": (
            "Always re-validate structured output at the trust boundary with the same schema, even when "
            "constrained decoding is on. Parse-don't-validate: reject (do not coerce) anything that fails, and "
            "never let an unvalidated field flow into a tool call or persistence layer."
        ),
        "verification_checks": [
            "a schema validator runs on every model output before use",
            "validation failure produces a typed rejection, not silent coercion",
            "no code path consumes a raw/unvalidated field",
        ],
    },
    {
        "topic_id": "SO-REPAIR-005",
        "title": "Invalid / partial output repair boundary",
        "concern": "failure_handling",
        "contract_type": "repair",
        "tags": [
            "invalid",
            "partial",
            "repair",
            "retry",
            "malformed",
            "truncated",
            "incomplete",
            "fix",
            "reprompt",
            "recover",
        ],
        "source": "Bounded-retry / re-ask reliability patterns",
        "version": "2024",
        "recommendation": (
            "Define a bounded repair policy: on validation failure, re-ask once with the validator error "
            "attached, cap total attempts (e.g. 2), and treat exhaustion as a typed failure — never emit a "
            "best-effort partial object. Do NOT hand-patch model JSON with regex in production."
        ),
        "verification_checks": [
            "repair attempts are bounded and counted",
            "exhausted repair yields a typed failure (not a partial object)",
            "no ad-hoc string/regex mutation of model JSON",
        ],
    },
    {
        "topic_id": "SO-STREAM-006",
        "title": "Streaming / partial-object handling",
        "concern": "failure_handling",
        "contract_type": "streaming",
        "tags": ["streaming", "partial", "incomplete", "truncated", "stream", "buffer"],
        "source": "Incremental-parse / streaming structured-output practice",
        "version": "2024",
        "recommendation": (
            "When streaming a structured response, buffer until a complete, schema-valid object is available "
            "before acting on it; expose partial state to the UI only, never to downstream automation or a "
            "tool call. Guard against acting on a truncated object at stream end."
        ),
        "verification_checks": [
            "downstream automation consumes only complete validated objects",
            "stream truncation is detected and treated as failure",
            "partial fields never trigger side effects",
        ],
    },
    {
        "topic_id": "SO-TOOL-007",
        "title": "Tool-call argument reliability",
        "concern": "tool_call_reliability",
        "contract_type": "function_call",
        "tags": [
            "tool call",
            "tool-call",
            "function call",
            "function-calling",
            "tool argument",
            "arguments",
            "tool use",
            "parameters",
            "call signature",
            "unsafe execution",
        ],
        "source": "Function-calling reliability + least-privilege tool design",
        "version": "2024",
        "recommendation": (
            "Give each tool a strict parameter schema (enums, bounds, no free-form command strings), validate "
            "arguments before dispatch, and design tools least-privilege so a hallucinated argument cannot "
            "cause an unsafe action. Never pass an unvalidated model field as an executable command."
        ),
        "verification_checks": [
            "every tool parameter is schema-constrained (no free-form command field)",
            "arguments are validated before the tool is dispatched",
            "tools are least-privilege; a bad argument cannot escalate",
        ],
    },
    {
        "topic_id": "SO-ESCALATE-008",
        "title": "Escalation & human-review fallback",
        "concern": "escalation",
        "contract_type": "escalation",
        "tags": [
            "escalate",
            "escalation",
            "human",
            "review",
            "approve",
            "approval",
            "confidence",
            "uncertain",
            "hitl",
            "human-in-the-loop",
            "when to stop",
        ],
        "source": "HITL / graceful-degradation reliability practice",
        "version": "2024",
        "recommendation": (
            "Define an explicit escalation policy: when validation/repair is exhausted or a low-confidence "
            "signal is present on a high-impact action, stop and route to a human/approval gate rather than "
            "proceeding. The reliability contract must have a defined 'do not proceed' terminal state."
        ),
        "verification_checks": [
            "a 'do not proceed' terminal state exists for high-impact actions",
            "repair-exhaustion routes to human/approval, not best-effort auto-proceed",
            "escalation criteria are explicit and testable",
        ],
    },
]


class ReliabilityKB:
    """Deterministic intent classification + retrieval over the seeded reliability KB."""

    CONCERNS: tuple[str, ...] = tuple(_CONCERN_KEYWORDS.keys())

    @staticmethod
    def classify(question: str, declared_constraints: str | None = None) -> dict[str, Any]:
        """Classify the technical question into one/more reliability concerns (deterministic)."""
        text = f"{question or ''} {declared_constraints or ''}".lower()
        scored: list[tuple[int, str]] = []
        for concern, keywords in _CONCERN_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits:
                scored.append((hits, concern))
        scored.sort(key=lambda x: (-x[0], x[1]))
        concerns = [c for _, c in scored]
        primary = concerns[0] if concerns else "unclassified"
        return {"primary_intent": primary, "concerns": concerns}

    @staticmethod
    def retrieve(query: str, concerns: list[str] | None = None, top_k: int = 4) -> list[dict[str, Any]]:
        """Keyword/tag + concern-scored retrieval. [] when nothing matches (out-of-scope)."""
        q = (query or "").lower()
        concern_set = set(concerns or [])
        scored: list[tuple[int, dict[str, Any]]] = []
        for rec in KB:
            score = sum(2 for t in rec["tags"] if t in q)
            if rec["concern"] in concern_set:
                score += 3
            if rec["title"].lower() in q:
                score += 4
            if score:
                scored.append((score, rec))
        scored.sort(key=lambda x: (-x[0], x[1]["topic_id"]))
        out: list[dict[str, Any]] = []
        for score, rec in scored[:top_k]:
            out.append(
                {
                    "topic_id": rec["topic_id"],
                    "title": rec["title"],
                    "concern": rec["concern"],
                    "contract_type": rec["contract_type"],
                    "recommendation": rec["recommendation"],
                    "verification_checks": rec["verification_checks"],
                    "source": rec["source"],
                    "version": rec["version"],
                    "score": score,
                }
            )
        return out

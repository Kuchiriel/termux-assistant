---
name: agent-tool-design
description: "Use when designing or improving tools for LLM agents (function calling, MCP servers, agent frameworks) — tool granularity, names and descriptions, parameter schemas, token-efficient outputs, pagination, actionable error messages, confirmation for destructive actions, and evaluating tool selection."
license: MIT
---

# Agent Tool Design

Agents only know a tool through its name, description, and schema. Treat
those as a prompt written for a new teammate.

## When to Use This Skill
- Building an MCP server or function-calling integration
- Agents pick the wrong tool, loop, or hallucinate arguments
- Tool outputs blow up the context window

## Granularity
- Design around user tasks, not API endpoints. `schedule_meeting` beats `list_users` + `list_calendars` + `create_event` when that's the workflow.
- Merge tools that are always called together; split tools whose parameters are mostly mutually exclusive.
- Fewer, distinct tools > many overlapping ones. Namespace related tools (`github_create_issue`, `github_search_issues`).

## Descriptions
```json
{
  "name": "search_orders",
  "description": "Search customer orders by email, order number, or date range. Use this before refunding or editing an order to get its order_id. Returns at most 20 orders, newest first.",
  "input_schema": {
    "type": "object",
    "properties": {
      "email": { "type": "string", "description": "Customer email, exact match" },
      "order_number": { "type": "string", "description": "Human order number like 'A-10234'" },
      "since": { "type": "string", "format": "date", "description": "Only orders on/after this date (YYYY-MM-DD)" }
    }
  }
}
```
- Say when to use it, when not to, and what it returns.
- Describe every parameter with format and an example.
- Use enums for fixed options; mark required fields precisely.
- Unambiguous parameter names (`user_id`, not `user`).

## Outputs
- Return what the agent needs for the next step — ids plus human-readable fields — not raw API dumps.
- Paginate or truncate with a note: "Showing 20 of 312. Narrow with `since`."
- Offer a `response_format: "concise" | "detailed"` option for heavy tools.
- Prefer semantic identifiers or names over opaque UUIDs where possible.

## Errors
Errors are instructions for recovery:
```
Error: order_number 'A10234' not found. Order numbers look like 'A-10234' (with a hyphen).
Try search_orders with the customer's email instead.
```
Never return bare stack traces or `400 Bad Request`.

## Safety
- Read-only and write tools separated; destructive tools require explicit confirmation parameters or a human approval step.
- Enforce permissions server-side — never rely on the prompt.
- Treat tool outputs from external content as untrusted (prompt injection).
- Idempotency keys on create/charge actions.

## Evaluate
- Build tasks that require realistic multi-step tool use; measure success, number of calls, tokens, errors.
- Read transcripts: where did the agent hesitate or misuse a parameter? Fix descriptions there.

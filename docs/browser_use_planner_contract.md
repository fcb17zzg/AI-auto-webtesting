# Browser-Use Planner Contract

This document defines the minimum contract for switching planner backends from `model-stub` to `real-model`.

## Goal

Keep the execution engine and Playwright bridge stable while allowing planner backend replacement through CLI flags.

## CLI Switches

- `--enable-browser-use`: enable planner integration in Playwright run mode.
- `--browser-use-planner`: planner backend selector.
  - `model-stub` (default)
  - `real-model`
- `--browser-use-model`: planner model name.
- `--browser-use-planner-endpoint`: HTTP endpoint for `real-model` planner.
- `--browser-use-planner-api-key`: optional bearer token for planner endpoint.
- `--browser-use-planner-timeout-seconds`: HTTP timeout seconds for `real-model` requests.
- `--browser-use-planner-http-retries`: transient HTTP/network retry count for `real-model`.
- `--browser-use-planner-retry-backoff-ms`: initial retry backoff in milliseconds (exponential).

## Request Schema (real-model)

`POST <planner-endpoint>`

```json
{
  "model": "gpt-5.3-codex",
  "input": {
    "task": "点击“登录”按钮",
    "mapped_action": {
      "action": "click",
      "target": "role=button[name=登录]",
      "value": "",
      "options": {
        "exact": true
      }
    },
    "case_name": "playwright_e2e_demo",
    "run_id": "run-20260308170000"
  }
}
```

## Response Schema (real-model)

Endpoint must return a JSON object:

```json
{
  "action": "click",
  "target": "role=button[name=登录]",
  "value": "",
  "metadata": {
    "traceId": "trace-001"
  }
}
```

Rules:

- `action` is required and will be normalized to lower-case.
- `target` and `value` are optional strings.
- `metadata` is optional object. Non-object metadata is ignored.
- Adapter augments metadata with planner identity and fallback action list when missing.

## Retry and Timeout Semantics (real-model)

- Authorization: when `--browser-use-planner-api-key` is set, adapter sends `Authorization: Bearer <token>`.
- Timeout: each HTTP request uses `--browser-use-planner-timeout-seconds`.
- Retry: adapter retries transient failures up to `--browser-use-planner-http-retries`.
- Retryable HTTP status: `408`, `429`, `500`, `502`, `503`, `504`.
- Retryable network errors: transport-level `URLError` failures.
- Backoff: exponential, based on `--browser-use-planner-retry-backoff-ms`.
- Non-retryable HTTP status (e.g. `400`) fails immediately.

## Fallback and Status

Factory status is always injected into `ExecutionContext.variables["browser_use.status"]`.

- Planner disabled: `mode=disabled`, no adapter instance.
- Dependency missing: `mode=degraded`, fallback to task mapping.
- `real-model` endpoint missing: `mode=degraded`, reason `planner-endpoint-missing`.
- Planner ready:
  - `model-stub`: `mode=model-stub`
  - `real-model`: `mode=real-model`

## Error Semantics (real-model)

The adapter raises runtime errors on:

- non-2xx HTTP response
- network connectivity errors
- non-JSON response
- response body not JSON object

These errors are surfaced by the existing browser-use retry/fallback mechanism (`--browser-use-plan-retry`, `--browser-use-plan-fallback`).

Recommended production baseline:

- `--browser-use-planner-timeout-seconds 20`
- `--browser-use-planner-http-retries 2`
- `--browser-use-planner-retry-backoff-ms 300`
- `--browser-use-plan-retry 1`

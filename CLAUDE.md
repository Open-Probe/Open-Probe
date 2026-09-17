# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape

Four loosely coupled pieces:

| Path | What it is |
| --- | --- |
| `src/deepsearch/` | The agent itself — a LangGraph ReWOO graph. Installed as the top-level package `deepsearch` (see `[tool.hatch.build.targets.wheel]`), *not* `src.deepsearch`. |
| `backend/` | FastAPI wrapper that streams graph events to the UI over WebSocket. Imports `deepsearch` via a `sys.path` hack, not as a dependency. |
| `frontend/` | Next.js 14 App Router UI (zustand + WebSocket). |
| `evals/` | FRAMES-style batch runner + LLM grader. |

## Commands

```bash
# Install (single install covers agent + backend + evals)
pip install -e .

# CLI — the fastest way to exercise the agent end to end
python -m src.deepsearch.cli search "How tall is the Burj Khalifa?"
python -m src.deepsearch.cli search --max-replan 2 "..."
python -m src.deepsearch.cli search --interactive

# Backend (run from repo root; start_server.py puts backend/ on sys.path)
python backend/start_server.py            # :8000, --reload on
LOG_LEVEL=DEBUG uvicorn app.main:app --reload --port 8000   # from backend/
# docs at /docs, health at /health, stats at /stats, ws at /ws

# Frontend
cd frontend && npm install && npm run dev  # :3000
npm run build && npm run lint

# Evals: run -> grade -> score (each step rewrites/reads a JSONL)
python evals/eval_tasks.py --eval-tasks ./evals/datasets/frames_test_set.csv --parallel-workers 8
python evals/autograde_df.py --df_path <out.jsonl> --provider sonic     # or mistral/gemini/huggingface/gaudi
python evals/accuracy.py --df_path <out.jsonl>                         # fraction graded "A"
```

There is **no test framework** (no pytest, no frontend tests). `test_deepsearch.py` is a hand-run smoke script with a hardcoded query — edit the `query` variable and `python test_deepsearch.py`. `eval_tasks.py` resumes by skipping questions already present in the output JSONL, so reruns are cheap.

## Architecture

### The ReWOO loop (`src/deepsearch/graph.py`)

Everything routes through a single `master` node; there are no static edges except `START -> master`. Each node returns a `Command(goto=..., update=...)`, so the control flow lives entirely in `master`'s branch order:

1. `needs_replan` and budget left → `replan`; budget exhausted → terminal failure result.
2. `result is not None` → `END`.
3. `steps == []` → `plan`.
4. `len(results) == len(steps)` → `solve`.
5. Otherwise dispatch step `len(results)` by tool name.

`plan` prompts the LLM for a ReWOO plan and parses it with `REGEX_PATTERN` into 4-tuples `(step_plan, "#E1", tool, tool_input)`. Anything the regex doesn't match is silently dropped, so plan-prompt edits and that regex must stay in sync. `results` is a dict keyed by `#E<n>`; **step position is `len(results)`**, so results must be appended in plan order and never sparsely.

Three tools:
- `Search` → the `search` node, but the tool input is first rewritten by `reword_tool_input` (a separate LLM call) into a search query.
- `Code` → the `code` node.
- `LLM` → executed *inline inside `master`*, not as a node. This is why the backend adapter needs `_handle_master_node` to synthesize UI steps for LLM tool calls.

`#E` references are resolved by `substitute_evidence`, which matches whole `#E\d+` tokens in one regex pass (naive per-key replacement would let `#E1` clobber `#E10`). Unresolved references are left as-is.

Failure signals all funnel into the same mechanism — set `needs_replan: True` and `goto: "master"`: search returned no extractable `<answer>`, the search API failed, code execution failed, or the LLM emitted `<replan>`. `replan` generates a reflection, bumps `replan_iter`, and `plan` wipes `results`/`sources`/`result` when replanning.

LLM responses are parsed by tag extraction (`extract_content(text, "answer")`) and `remove_think_cot` strips `<think>` blocks from reasoning models. A `None` from `extract_content` is the "unsatisfactory" signal, so prompts must keep emitting those tags.

### Model + reranker selection is import-time

There is one LLM provider: **Sonic**, an internal OpenAI-compatible gateway for approved models. `initialize_models()` runs at module import and builds three `ChatOpenAI` clients (via `_sonic_model`) against Sonic's OpenAI-compatible `POST /chat/completions`. It raises `ValueError` if `SONIC_JWT` is unset.

- Sonic mounts chat/responses/messages both with and without `/v1`, but `GET /v1/models` exists *only* prefixed — so keep the suffix.
- Models are env-overridable: `SONIC_PLAN_MODEL` (`claude-opus-5`), `SONIC_COMMON_MODEL` / `SONIC_CODE_MODEL` (`claude-sonnet-5`). `GET /chat/models` lists what's available, returning `{value, cursor, message}` rather than OpenAI's `{data: [...]}`.
- `SONIC_JWT` takes either a PAT or an Entra JWT and is passed **only** as the OpenAI `api_key` → `Authorization: Bearer`; Sonic detects the scheme from the token's shape. Never add an `api-key` header: Sonic checks that one first as a PAT-only lookup, so a JWT there 401s before `Authorization` is read. PAT is testing-only; production needs the JWT.
- Sonic's chat body has **no `max_tokens`** and silently drops unknown fields, `stream: true` returns one JSON body instead of SSE, and `session_id`/`include_history` persist nothing. There is **no embeddings or rerank endpoint** in production — which is why the rerankers still talk to Jina / a local TEI server.

Reranker selection is also import-time: `RERANKER_SERVER_HOST_IP` + `RERANKER_SERVER_PORT` set → `LocalReranker` (`BAAI/bge-reranker-base` over HTTP), else `JinaReranker`. Consequence: **`load_dotenv()` must have run before `deepsearch.graph` is imported**, and switching models means changing env vars, not arguments. `PythonREPL()` is also instantiated at import.

Three model handles are used for different roles — `PLAN_MODEL` (plan/replan/reflection/solve/LLM tool), `COMMON_MODEL` (query rewrite, search summary, explanation), `CODE_MODEL`.

### Search pipeline (`src/deepsearch/web_search/`)

`serp_search.create_search_api` → `SerperAPI` (or `SearXNGAPI`) returns a `SearchResult` wrapper with `.data` / `.error` / `.failed` — check `.failed`, it never raises. Then `SourceProcessor.process_sources` scrapes the top `MAX_SOURCES_PER_SEARCH` (default 2) links with crawl4ai, chunks each page, reranks chunks against the query, and writes the reranked text back into the *same* `organic[i]` dicts. It always returns `sources.data` even on failure, so callers get one shape. `context_builder.build_context` then flattens organic results + answer box + top stories into the prompt context.

Note the env-var seam: `graph.py` reads `WEB_SEARCH_API_KEY` and passes it explicitly; `SerperConfig.from_env()` (the fallback path when no key is passed) reads `SERPER_API_KEY`.

### Backend ↔ agent bridge (`backend/app/services/deepsearch_adapter.py`)

The adapter is where graph internals become UI. It `graph.astream(...)`s the same initial state dict as the CLI, accumulates node deltas into `final_state`, and per node emits a `ThinkingStep` twice — once `RUNNING`, then `COMPLETED` with detailed content (with a deliberate `asyncio.sleep(1.0)` between so the UI can animate). It is defensive by design: every step tuple is length-checked and every handler wrapped, because malformed plan parses reach it. If `deepsearch` can't be imported it logs a warning and runs in **mock mode** rather than failing.

State flows one way (graph → WS events); `SessionManager` keeps everything in memory with a cleanup task, and `WebSocketManager` broadcasts. Both are module-level singletons wired in `main.py` and handed out via `dependencies.py`.

Anything added to `ReWOOState` needs matching entries in *four* initial-state dicts: `cli.py`, `test_deepsearch.py`, `evals/eval_tasks.py`, and the adapter.

### Frontend

`useSearch` is a zustand store holding the whole chat; `useWebSocket` maps WS message types (`step_update`, `search_complete`, `search_cancelled`, `error`, `session_reset`) onto store actions. Backend URLs come from `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`, defaulted in `next.config.js`.

## Gotchas

- **`frontend/src/lib/` is missing from git.** `.gitignore:17` has a bare `lib/` (Python packaging boilerplate) which excludes it, yet nearly every component imports `@/lib/utils`, `@/lib/api`, `@/lib/websocket`. A fresh clone's frontend will not build until those are recreated. Use `git check-ignore -v <path>` before assuming a frontend file is simply absent.
- **`code` nodes execute LLM-generated Python locally, unsandboxed** via `langchain_experimental` `PythonREPL`.
- `PythonREPL.run` returns tracebacks as ordinary strings and `""` for code that computes without printing, so `python_repl_tool` appends a sentinel print (`REPL_SUCCESS_SENTINEL`) to tell success from failure. Don't "simplify" that back to a `None` check.
- `SourceProcessor._process_html_content` writes `testing_reranked_documents.json` (and a `data/` dir) into the **current working directory** on every search — a debug artifact, already committed under `backend/`.
- The graph prints heavily to stdout with emoji markers (`====PLAN====`, `🔍`, …); that output is the primary debugging surface for the agent. The backend uses `loguru`-style logging via `app/utils/logging.py` instead.
- Recursion limits differ by entrypoint (CLI 30, adapter 50, evals 40) as does `max_replan_iter` (1, 1, 2).

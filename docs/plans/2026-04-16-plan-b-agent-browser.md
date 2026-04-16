# Plan B: Agent Browser Adapter Refactor

## Goal

Introduce an optional agent-browser backend for XiaoHongShu browser automation while keeping the existing Chrome DevTools Protocol backend as the default fallback.

## Constraints

- Preserve the current CDP flow unless explicitly opting into the new backend.
- Keep the top-level skill tree and nested `xiaohongshu-skills` package in sync for runtime files and tests.
- Use test-first changes for each slice.
- Avoid broad workflow rewrites until the adapter contract is stable.

## Slice 1: Adapter Skeleton

1. Add tests for parsing browser accessibility snapshot lines into semantic elements.
2. Add tests for selecting the agent-browser backend through configuration.
3. Implement `agent_browser_adapter.py` with snapshot parsing and a small backend interface.
4. Wire backend selection into `chrome_launcher.ensure_chrome()` without changing default behavior.
5. Mirror runtime/test changes into `xiaohongshu-skills/`.
6. Run focused tests first, then broader related tests.

## Expected Verification

- `python3 -m unittest discover -s tests -p 'test_agent_browser_adapter.py' -v`
- `python3 -m unittest discover -s tests -p 'test_chrome_launcher.py' -v`
- Equivalent commands under `xiaohongshu-skills/` after mirroring.

## Status Update

- Slice 1 is complete.
- `scripts/browser_adapter.py` now wraps the external `agent-browser` CLI.
- `scripts/chrome_launcher.py` and `xiaohongshu-skills/scripts/chrome_launcher.py` now support the optional `XHS_BROWSER_BACKEND=agent-browser` path while keeping `cdp` as the default.
- Focused adapter tests pass, and the broader unittest discovery runs for both trees completed successfully.
- A local git repository now exists at the skill root with an initial snapshot commit so the next refactor slices have a rollback point.

## Slice 2: Minimal Browser/Page Compatibility for Login Flow

### Objective

Build the smallest possible compatibility layer in `scripts/xhs/cdp.py` so the `agent-browser` backend can support the login flow without attempting a full Page API rewrite.

### Why this slice

- `cli.py` and `publish_pipeline.py` already enter through `Browser(...)` and `Page` flows.
- The report identifies `xhs/cdp.py` as the next architectural seam after the launcher/backend selection work.
- Login uses a smaller, more testable subset of `Page` methods than publish or feed-detail flows.
- This gives us a real end-to-end path before tackling the much larger `page.evaluate(...)` surface used elsewhere.

### Login-driven minimum method set

The compatibility slice should cover only the methods that the login module actually needs first:

- `Browser.new_page()`
- `Browser.get_existing_page()`
- `Page.navigate(url)`
- `Page.wait_for_load()`
- `Page.has_element(selector)`
- `Page.wait_for_element(selector, timeout=...)`
- `Page.click_element(selector)`
- `Page.type_text(text, delay_ms=...)`
- `Page.get_element_text(selector)`
- `Page.get_element_attribute(selector, name)`

### Test-first plan

1. Add a new focused test module, e.g. `tests/test_agent_browser_cdp_bridge.py`.
2. First write failing tests for a backend-switched `Browser`:
   - when `XHS_BROWSER_BACKEND=agent-browser`, `Browser.new_page()` returns an adapter-backed page object;
   - `Browser.get_existing_page()` reuses the current session/page instead of opening a second page when a current URL exists.
3. Write failing tests for the adapter-backed `Page` behaviors needed by login:
   - `navigate(url)` delegates to `AgentBrowserAdapter.open_url(url)`;
   - `wait_for_load()` polls a small readiness expression via adapter evaluation until `document.readyState === "complete"`;
   - `has_element(selector)` uses adapter evaluation and returns a boolean;
   - `wait_for_element(selector)` retries until found, then returns a lightweight selector token or truthy handle compatible with current login usage;
   - `click_element(selector)` resolves the selector to an interactive element and clicks it;
   - `type_text(text, delay_ms=...)` types into the currently focused field;
   - `get_element_text(selector)` and `get_element_attribute(selector, name)` read values through adapter evaluation.
4. Keep the old CDP implementation intact for the default backend path.
5. Mirror the same tests and runtime changes into `xiaohongshu-skills/` only after the main tree is green.

### Production changes expected for Slice 2

- Extend `scripts/browser_adapter.py` with the minimum primitives needed by the tests, most likely:
  - `evaluate(expression)`
  - `press_key(key)`
  - optional selector helper(s) if snapshot lookup alone is not sufficient.
- Introduce a small adapter-backed page class inside `scripts/xhs/cdp.py` instead of rewriting the entire module at once.
- Gate the new `Browser` behavior behind `get_browser_backend()` so the current CDP code remains the default fallback.
- Reuse existing `AgentBrowserAdapter.ensure_ready()` behavior rather than inventing a second launch path.

### Explicitly deferred to later slices

These are intentionally out of scope for Slice 2:

- broad `page.evaluate(...)` compatibility for publish/search/detail flows
- contenteditable rich-text editing
- file upload and drag/drop behaviors
- mouse wheel/box-model helpers
- screenshot parity beyond what the adapter already supports
- multi-page/tab lifecycle fidelity beyond `new_page()` / `get_existing_page()`

### Verification for Slice 2

Run in this order:

1. `python3 -m unittest discover -s tests -p 'test_agent_browser_cdp_bridge.py' -v`
2. `python3 -m unittest discover -s tests -p 'test_agent_browser_adapter.py' -v`
3. `python3 -m unittest discover -s tests -v`
4. Mirror-tree equivalents under `xiaohongshu-skills/` after syncing changes.

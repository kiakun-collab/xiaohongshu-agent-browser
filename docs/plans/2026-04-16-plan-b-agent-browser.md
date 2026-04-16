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

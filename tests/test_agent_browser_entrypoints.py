from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cli


class AgentBrowserCliConnectTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_context = dict(cli._EXECUTION_CONTEXT)

    def tearDown(self) -> None:
        cli._EXECUTION_CONTEXT.clear()
        cli._EXECUTION_CONTEXT.update(self._original_context)

    @staticmethod
    def _args() -> argparse.Namespace:
        return argparse.Namespace(host="127.0.0.1", port=9333, account="demo")

    def test_connect_uses_agent_browser_backend_without_cdp_http_probe(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("cli._profile_dir", return_value="/tmp/xhs-profile"),
            mock.patch("chrome_launcher.ensure_chrome", return_value=True),
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
            mock.patch("xhs.cdp.get_agent_browser_adapter", create=True, return_value=adapter),
            mock.patch("xhs.cdp.requests.get", side_effect=AssertionError("should not probe CDP HTTP endpoint")),
        ):
            browser, page = cli._connect(self._args())

        self.assertEqual(page.__class__.__name__, "AgentBrowserPage")
        self.assertIs(cli._EXECUTION_CONTEXT["page"], page)
        self.assertGreaterEqual(adapter.ensure_ready.call_count, 2)
        adapter.open_url.assert_not_called()
        browser.close_page(page)

    def test_connect_existing_reuses_agent_browser_session_without_cdp_http_probe(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True
        adapter.get_current_url.return_value = "https://www.xiaohongshu.com/explore"

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("cli._profile_dir", return_value="/tmp/xhs-profile"),
            mock.patch("cli._resolved_account", return_value="demo"),
            mock.patch("chrome_launcher.ensure_chrome", return_value=True),
            mock.patch("runtime_state.load_active_page", return_value={"target_id": "agent-browser"}),
            mock.patch("runtime_state.clear_active_page") as mock_clear,
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
            mock.patch("xhs.cdp.get_agent_browser_adapter", create=True, return_value=adapter),
            mock.patch("xhs.cdp.requests.get", side_effect=AssertionError("should not probe CDP HTTP endpoint")),
        ):
            browser, page = cli._connect_existing(self._args())

        self.assertEqual(page.__class__.__name__, "AgentBrowserPage")
        self.assertIs(cli._EXECUTION_CONTEXT["page"], page)
        adapter.get_current_url.assert_called_once_with()
        mock_clear.assert_not_called()
        browser.close_page(page)


if __name__ == "__main__":
    unittest.main()

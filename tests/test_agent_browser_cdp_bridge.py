from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from browser_adapter import AgentBrowserAdapter
from xhs.cdp import AgentBrowserPage, Browser
from xhs.errors import CDPError, ElementNotFoundError


class AgentBrowserBrowserTest(unittest.TestCase):
    """Browser 类在 agent-browser 后端下的行为测试。"""

    def test_new_page_returns_adapter_backed_page_when_backend_is_agent_browser(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.open_url.return_value = True

        with mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False), mock.patch(
            "xhs.cdp.get_agent_browser_adapter", return_value=adapter
        ):
            browser = Browser()
            browser.connect()
            page = browser.new_page(url="https://example.com")

        self.assertIsInstance(page, AgentBrowserPage)
        self.assertEqual(page._adapter, adapter)
        adapter.open_url.assert_called_once_with("https://example.com")

    def test_get_existing_page_reuses_session_when_url_exists(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.get_current_url.return_value = "https://example.com"

        with mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False), mock.patch(
            "xhs.cdp.get_agent_browser_adapter", return_value=adapter
        ):
            browser = Browser()
            browser.connect()
            page = browser.get_existing_page()

        self.assertIsInstance(page, AgentBrowserPage)
        adapter.get_current_url.assert_called_once_with()

    def test_get_existing_page_returns_none_when_no_current_url(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.get_current_url.return_value = None

        with mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False), mock.patch(
            "xhs.cdp.get_agent_browser_adapter", return_value=adapter
        ):
            browser = Browser()
            browser.connect()
            page = browser.get_existing_page()

        self.assertIsNone(page)


class AgentBrowserPageTest(unittest.TestCase):
    """AgentBrowserPage 最小兼容层测试。"""

    def test_navigate_delegates_to_adapter_open_url(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.open_url.return_value = True
        page = AgentBrowserPage(adapter)

        page.navigate("https://example.com")

        adapter.open_url.assert_called_once_with("https://example.com")

    def test_navigate_raises_on_failure(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.open_url.return_value = False
        page = AgentBrowserPage(adapter)

        with self.assertRaises(CDPError):
            page.navigate("https://example.com")

    def test_wait_for_load_polls_ready_state(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.side_effect = ["interactive", "complete"]
        page = AgentBrowserPage(adapter)

        page.wait_for_load(timeout=1.0)

        self.assertEqual(adapter.evaluate.call_count, 2)
        adapter.evaluate.assert_any_call("document.readyState")

    def test_has_element_returns_boolean(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        result = page.has_element("#login")

        self.assertTrue(result)
        adapter.evaluate.assert_called_once()
        self.assertIn("document.querySelector", adapter.evaluate.call_args[0][0])

    def test_wait_for_element_retries_and_returns_selector(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.side_effect = [False, False, True]
        page = AgentBrowserPage(adapter)

        result = page.wait_for_element("#btn", timeout=2.0)

        self.assertEqual(result, "#btn")
        self.assertGreaterEqual(adapter.evaluate.call_count, 3)

    def test_click_element_uses_js_click(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        page.click_element("#submit")

        adapter.evaluate.assert_called_once()
        self.assertIn(".click()", adapter.evaluate.call_args[0][0])

    def test_click_element_raises_when_not_found(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        with self.assertRaises(ElementNotFoundError):
            page.click_element("#missing")

    def test_type_text_appends_to_active_element(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        page.type_text("abc", delay_ms=0)

        self.assertEqual(adapter.evaluate.call_count, 3)
        calls = [call[0][0] for call in adapter.evaluate.call_args_list]
        for char in "abc":
            self.assertTrue(any(char in c for c in calls), f"character '{char}' not found in evaluate calls")

    def test_get_element_text(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = "Hello"
        page = AgentBrowserPage(adapter)

        result = page.get_element_text("#title")

        self.assertEqual(result, "Hello")
        self.assertIn("textContent", adapter.evaluate.call_args[0][0])

    def test_get_element_attribute(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = "btn-primary"
        page = AgentBrowserPage(adapter)

        result = page.get_element_attribute("#btn", "class")

        self.assertEqual(result, "btn-primary")
        self.assertIn("getAttribute", adapter.evaluate.call_args[0][0])


if __name__ == "__main__":
    unittest.main()

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
from xhs.cdp import AgentBrowserPage
from xhs.errors import CDPError, ElementNotFoundError


class AgentBrowserPageCompletenessTest(unittest.TestCase):
    """补齐 AgentBrowserPage 中缺失的 Page API 测试。"""

    # --- evaluate / function ---

    def test_evaluate_function(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = 42
        page = AgentBrowserPage(adapter)

        result = page.evaluate_function("() => { return 42; }")

        self.assertEqual(result, 42)
        adapter.evaluate.assert_called_once_with("(() => { return 42; })()")

    # --- selector ---

    def test_query_selector_returns_object_id_placeholder(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = {"x": 1}
        page = AgentBrowserPage(adapter)

        result = page.query_selector("#app")

        self.assertEqual(result, 'jsref:#app')
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("querySelector", expr)

    def test_query_selector_returns_none_when_missing(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        result = page.query_selector("#missing")

        self.assertIsNone(result)

    def test_query_selector_all_returns_placeholders(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = 3
        page = AgentBrowserPage(adapter)

        result = page.query_selector_all(".item")

        self.assertEqual(result, ['jsref:.item[0]', 'jsref:.item[1]', 'jsref:.item[2]'])

    # --- scroll ---

    def test_scroll_to(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.scroll_to(100, 200)

        adapter.evaluate.assert_called_once_with("window.scrollTo(100, 200)")

    def test_scroll_element_into_view(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.scroll_element_into_view("#btn")

        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("scrollIntoView", expr)
        self.assertIn('"#btn"', expr)

    def test_scroll_nth_element_into_view(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.scroll_nth_element_into_view(".card", 2)

        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("querySelectorAll", expr)
        self.assertIn("[2]", expr)

    def test_get_scroll_top(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = 123
        page = AgentBrowserPage(adapter)

        result = page.get_scroll_top()

        self.assertEqual(result, 123)
        adapter.evaluate.assert_called_once()

    def test_get_viewport_height(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = 800
        page = AgentBrowserPage(adapter)

        result = page.get_viewport_height()

        self.assertEqual(result, 800)
        adapter.evaluate.assert_called_once_with("window.innerHeight")

    # --- interaction ---

    def test_dispatch_wheel_event(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.dispatch_wheel_event(300.0)

        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("WheelEvent", expr)
        self.assertIn("300.0", expr)

    def test_mouse_move(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.mouse_move(50.0, 100.0)

        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("MouseEvent", expr)
        self.assertIn("mousemove", expr)

    def test_hover_element(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = {"x": 100, "y": 200}
        page = AgentBrowserPage(adapter)

        page.hover_element("#link")

        exprs = [call[0][0] for call in adapter.evaluate.call_args_list]
        self.assertTrue(any("getBoundingClientRect" in e for e in exprs), "getBoundingClientRect not found in evaluate calls")
        self.assertTrue(any("mousemove" in e for e in exprs), "mousemove not found in evaluate calls")

    def test_inject_stealth_is_noop(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        page = AgentBrowserPage(adapter)

        page.inject_stealth()

        adapter.evaluate.assert_not_called()
        adapter.take_screenshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()

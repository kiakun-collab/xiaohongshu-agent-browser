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


class AgentBrowserPublishBridgeTest(unittest.TestCase):
    """AgentBrowserPage 对 publish flow 的扩展兼容层测试。"""

    def test_evaluate_delegates_to_adapter(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = {"url": "https://example.com"}
        page = AgentBrowserPage(adapter)

        result = page.evaluate("window.location.href")

        self.assertEqual(result, {"url": "https://example.com"})
        adapter.evaluate.assert_called_once_with("window.location.href")

    def test_wait_dom_stable_polls_html_length(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.side_effect = [100, 150, 150]
        page = AgentBrowserPage(adapter)

        page.wait_dom_stable(timeout=1.0, interval=0.1)

        self.assertEqual(adapter.evaluate.call_count, 3)
        adapter.evaluate.assert_any_call(
            "document.body ? document.body.innerHTML.length : 0"
        )

    def test_mouse_click_uses_element_from_point(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        page.mouse_click(100.0, 200.0)

        adapter.evaluate.assert_called_once()
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("elementFromPoint", expr)
        self.assertIn("100", expr)
        self.assertIn("200", expr)

    def test_get_elements_count(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = 5
        page = AgentBrowserPage(adapter)

        result = page.get_elements_count(".item")

        self.assertEqual(result, 5)
        adapter.evaluate.assert_called_once_with(
            'document.querySelectorAll(".item").length'
        )

    def test_input_text_sets_value_and_dispatches_events(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        page.input_text("#title", "hello world")

        adapter.evaluate.assert_called_once()
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn('document.querySelector("#title")', expr)
        self.assertIn('el.value = "hello world"', expr)
        self.assertIn("'input'", expr)
        self.assertIn("'change'", expr)

    def test_input_content_editable_inserts_text(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        page.input_content_editable("#editor", "line1\nline2")

        adapter.evaluate.assert_called_once()
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn('document.querySelector("#editor")', expr)
        self.assertIn("contenteditable", expr.lower())

    def test_remove_element(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.remove_element(".ad")

        adapter.evaluate.assert_called_once()
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn(".remove()", expr)

    def test_select_all_text(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.select_all_text("#input")

        adapter.evaluate.assert_called_once()
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn("el.select()", expr)

    def test_scroll_by(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.scroll_by(0, 500)

        adapter.evaluate.assert_called_once_with("window.scrollBy(0, 500)")

    def test_scroll_to_bottom(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = None
        page = AgentBrowserPage(adapter)

        page.scroll_to_bottom()

        adapter.evaluate.assert_called_once_with(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

    def test_capture_screenshot_delegates_to_adapter(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.take_screenshot.return_value = True
        page = AgentBrowserPage(adapter)

        result = page.capture_screenshot("/tmp/shot.png")

        self.assertEqual(result, "/tmp/shot.png")
        adapter.take_screenshot.assert_called_once_with("/tmp/shot.png")

    def test_set_file_input_dispatches_change_event(self) -> None:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.evaluate.return_value = True
        page = AgentBrowserPage(adapter)

        page.set_file_input("#file", ["/tmp/1.png"])

        adapter.evaluate.assert_called_once()
        expr = adapter.evaluate.call_args[0][0]
        self.assertIn('document.querySelector("#file")', expr)
        self.assertIn("DataTransfer", expr)
        self.assertIn("dispatchEvent", expr)


if __name__ == "__main__":
    unittest.main()

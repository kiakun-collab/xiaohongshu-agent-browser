from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from xhs import cdp


class AgentBrowserBrowserBridgeTest(unittest.TestCase):
    def test_connect_uses_agent_browser_backend_without_cdp_http_probe(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
            mock.patch("xhs.cdp.get_agent_browser_adapter", create=True, return_value=adapter),
            mock.patch("xhs.cdp.requests.get", side_effect=AssertionError("should not probe CDP HTTP endpoint")),
        ):
            browser = cdp.Browser(host="127.0.0.1", port=9333)
            browser.connect()

        adapter.ensure_ready.assert_called_once_with()

    def test_new_page_uses_agent_browser_backend_without_cdp_connect(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True
        adapter.open_url.return_value = True

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
            mock.patch("xhs.cdp.get_agent_browser_adapter", create=True, return_value=adapter),
            mock.patch.object(cdp.Browser, "connect", side_effect=AssertionError("should not use CDP connect")),
        ):
            browser = cdp.Browser(host="127.0.0.1", port=9333)
            page = browser.new_page("https://www.xiaohongshu.com/explore")

        self.assertEqual(page.__class__.__name__, "AgentBrowserPage")
        self.assertIs(page.adapter, adapter)
        adapter.ensure_ready.assert_called_once_with()
        adapter.open_url.assert_called_once_with("https://www.xiaohongshu.com/explore")

    def test_get_existing_page_reuses_current_agent_browser_session(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True
        adapter.get_current_url.return_value = "https://www.xiaohongshu.com/explore"

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
            mock.patch("xhs.cdp.get_agent_browser_adapter", create=True, return_value=adapter),
            mock.patch.object(cdp.Browser, "connect", side_effect=AssertionError("should not use CDP connect")),
        ):
            browser = cdp.Browser(host="127.0.0.1", port=9333)
            page = browser.get_existing_page()

        self.assertEqual(page.__class__.__name__, "AgentBrowserPage")
        self.assertIs(page.adapter, adapter)
        adapter.get_current_url.assert_called_once_with()
        adapter.open_url.assert_not_called()

    def test_close_page_closes_agent_browser_session(self) -> None:
        adapter = mock.Mock()
        page = cdp.AgentBrowserPage(adapter)

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
        ):
            browser = cdp.Browser(host="127.0.0.1", port=9333)
            browser.close_page(page)

        adapter.close.assert_called_once_with()


class AgentBrowserPageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = mock.Mock()
        self.page = cdp.AgentBrowserPage(self.adapter)

    def test_navigate_delegates_to_adapter_open_url(self) -> None:
        self.adapter.open_url.return_value = True

        self.page.navigate("https://www.xiaohongshu.com/explore")

        self.adapter.open_url.assert_called_once_with("https://www.xiaohongshu.com/explore")

    def test_wait_for_load_polls_document_ready_state_until_complete(self) -> None:
        self.adapter.evaluate.side_effect = ["loading", "interactive", "complete"]

        with mock.patch("xhs.cdp.time.sleep") as mock_sleep:
            self.page.wait_for_load(timeout=2.0)

        self.assertEqual(self.adapter.evaluate.call_count, 3)
        self.adapter.evaluate.assert_called_with("document.readyState")
        self.assertGreaterEqual(mock_sleep.call_count, 2)

    def test_has_element_uses_query_selector_boolean_expression(self) -> None:
        self.adapter.evaluate.return_value = True

        has_element = self.page.has_element(".login-container")

        self.assertTrue(has_element)
        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.querySelector", expression)
        self.assertIn(".login-container", expression)

    def test_wait_for_element_retries_until_selector_exists(self) -> None:
        self.adapter.evaluate.side_effect = [False, False, True]

        with mock.patch("xhs.cdp.time.sleep") as mock_sleep:
            handle = self.page.wait_for_element(".login-container", timeout=2.0)

        self.assertEqual(handle, ".login-container")
        self.assertEqual(self.adapter.evaluate.call_count, 3)
        self.assertGreaterEqual(mock_sleep.call_count, 2)

    def test_click_element_uses_selector_based_javascript_click(self) -> None:
        self.adapter.evaluate.return_value = True

        self.page.click_element("button.submit")

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.querySelector", expression)
        self.assertIn("button.submit", expression)
        self.assertIn("click()", expression)

    def test_type_text_delegates_to_adapter_typing_primitive(self) -> None:
        self.page.type_text("13800138000", delay_ms=80)

        self.adapter.type_text.assert_called_once_with("13800138000")

    def test_get_element_text_reads_text_content_via_adapter_evaluate(self) -> None:
        self.adapter.evaluate.return_value = "登录成功"

        text = self.page.get_element_text(".status")

        self.assertEqual(text, "登录成功")
        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("textContent", expression)
        self.assertIn(".status", expression)

    def test_get_element_attribute_reads_attribute_via_adapter_evaluate(self) -> None:
        self.adapter.evaluate.return_value = "data:image/png;base64,abc"

        value = self.page.get_element_attribute("img.qrcode", "src")

        self.assertEqual(value, "data:image/png;base64,abc")
        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("getAttribute", expression)
        self.assertIn("img.qrcode", expression)
        self.assertIn("src", expression)

    def test_wait_dom_stable_polls_until_markup_length_stops_changing(self) -> None:
        self.adapter.evaluate.side_effect = [128, 256, 256]

        with mock.patch("xhs.cdp.time.sleep") as mock_sleep:
            self.page.wait_dom_stable(timeout=2.0, interval=0.1)

        self.assertEqual(self.adapter.evaluate.call_count, 3)
        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.body", expression)
        self.assertGreaterEqual(mock_sleep.call_count, 2)

    def test_input_text_sets_value_and_dispatches_events_via_evaluate(self) -> None:
        self.page.input_text("input[name='keyword']", "春季穿搭")

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.querySelector", expression)
        self.assertIn("input[name='keyword']", expression)
        self.assertIn("春季穿搭", expression)
        self.assertIn("dispatchEvent(new Event('input'", expression)
        self.assertIn("dispatchEvent(new Event('change'", expression)

    def test_input_content_editable_updates_inner_text_via_evaluate(self) -> None:
        self.page.input_content_editable(".ql-editor", "第一行\n第二行")

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.querySelector", expression)
        self.assertIn(".ql-editor", expression)
        self.assertIn("innerText", expression)
        self.assertIn("第一行\\n第二行", expression)
        self.assertIn("dispatchEvent(new Event('input'", expression)

    def test_get_elements_count_delegates_to_adapter_count_command(self) -> None:
        self.adapter.get_count.return_value = 6

        count = self.page.get_elements_count(".note-card")

        self.assertEqual(count, 6)
        self.adapter.get_count.assert_called_once_with(".note-card")

    def test_scroll_by_uses_window_scroll_by_expression(self) -> None:
        self.page.scroll_by(320)

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("window.scrollBy", expression)
        self.assertIn("320", expression)

    def test_scroll_to_bottom_uses_document_height_expression(self) -> None:
        self.page.scroll_to_bottom()

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("window.scrollTo", expression)
        self.assertIn("document.body.scrollHeight", expression)

    def test_scroll_element_into_view_delegates_to_adapter_scroll_into_view(self) -> None:
        self.page.scroll_element_into_view(".comment-box")

        self.adapter.scroll_into_view.assert_called_once_with(".comment-box")

    def test_set_file_input_delegates_to_adapter_upload_files(self) -> None:
        files = ["/tmp/a.png", "/tmp/b.png"]

        self.page.set_file_input('input[type="file"]', files)

        self.adapter.upload_files.assert_called_once_with('input[type="file"]', files)

    def test_dispatch_wheel_event_delegates_to_adapter_mouse_wheel(self) -> None:
        self.page.dispatch_wheel_event(delta_x=0, delta_y=480)

        self.adapter.mouse_wheel.assert_called_once_with(0, 480)

    def test_mouse_click_delegates_to_adapter_mouse_click(self) -> None:
        self.page.mouse_click(12, 24)

        self.adapter.mouse_click.assert_called_once_with(12, 24)

    def test_press_key_delegates_to_adapter_press_key(self) -> None:
        self.page.press_key("Control+a")

        self.adapter.press_key.assert_called_once_with("Control+a")

    def test_remove_element_uses_selector_based_javascript_remove(self) -> None:
        self.page.remove_element(".toast")

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.querySelector", expression)
        self.assertIn(".toast", expression)
        self.assertIn("remove()", expression)

    def test_hover_element_delegates_to_adapter_hover_element(self) -> None:
        self.page.hover_element(".toolbar .item")

        self.adapter.hover_element.assert_called_once_with(".toolbar .item")

    def test_select_all_text_uses_selector_based_selection_expression(self) -> None:
        self.page.select_all_text("textarea")

        expression = self.adapter.evaluate.call_args.args[0]
        self.assertIn("document.querySelector", expression)
        self.assertIn("textarea", expression)
        self.assertIn("select()", expression)

    def test_capture_screenshot_delegates_to_adapter_and_returns_path(self) -> None:
        self.adapter.take_screenshot.return_value = True

        screenshot_path = self.page.capture_screenshot("/tmp/xhs-login.png")

        self.assertEqual(screenshot_path, "/tmp/xhs-login.png")
        self.adapter.take_screenshot.assert_called_once_with("/tmp/xhs-login.png")


if __name__ == "__main__":
    unittest.main()

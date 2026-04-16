from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from browser_adapter import AgentBrowserAdapter
from xhs.cdp import AgentBrowserPage


class AgentBrowserReadFlowsTest(unittest.TestCase):
    """轻量验证 feed / search / user_profile / comment / like_favorite 读取流程在 AgentBrowserPage 上的兼容性。"""

    @staticmethod
    def _stable_evaluate(expr: str) -> Any:
        if "document.readyState" in expr:
            return "complete"
        if "document.body ? document.body.innerHTML.length : 0" in expr:
            return 150
        return None

    def _make_page(self) -> tuple[AgentBrowserPage, mock.Mock]:
        adapter = mock.Mock(spec=AgentBrowserAdapter)
        adapter.open_url.return_value = True
        adapter.evaluate.side_effect = self._stable_evaluate
        return AgentBrowserPage(adapter), adapter

    # --- feeds flow ---

    def test_feeds_extract_flow(self) -> None:
        page, adapter = self._make_page()
        calls: list[str] = []
        def _evaluate(expr: str) -> Any:
            calls.append(expr)
            if "document.readyState" in expr:
                return "complete"
            if "document.body ? document.body.innerHTML.length : 0" in expr:
                return 150
            return {"feeds": [{"id": "1"}]}
        adapter.evaluate.side_effect = _evaluate

        page.navigate("https://www.xiaohongshu.com")
        page.wait_for_load()
        page.wait_dom_stable()
        result = page.evaluate("window.__INITIAL_STATE__")

        self.assertEqual(result, {"feeds": [{"id": "1"}]})
        adapter.open_url.assert_called_once_with("https://www.xiaohongshu.com")

    # --- search flow ---

    def test_search_extract_and_filter_flow(self) -> None:
        page, adapter = self._make_page()
        calls: list[str] = []
        def _evaluate(expr: str) -> Any:
            calls.append(expr)
            if "document.readyState" in expr:
                return "complete"
            if "document.body ? document.body.innerHTML.length : 0" in expr:
                return 200
            if "EXTRACT_SEARCH_JS" in expr:
                return {"notes": [{"id": "n1"}]}
            if "getBoundingClientRect" in expr:
                return {"x": 120, "y": 240}
            return True
        adapter.evaluate.side_effect = _evaluate

        page.navigate("https://www.xiaohongshu.com/search_result")
        page.wait_for_load()
        page.wait_dom_stable()
        result = page.evaluate("EXTRACT_SEARCH_JS")
        page.hover_element(".filter-button")

        self.assertEqual(result, {"notes": [{"id": "n1"}]})
        adapter.open_url.assert_called_once()

    # --- user_profile flow ---

    def test_user_profile_extract_flow(self) -> None:
        page, adapter = self._make_page()
        calls: list[str] = []
        profile_results = [
            {"user_id": "u123", "nickname": "Alice"},
            {"notes": [{"id": "n1"}, {"id": "n2"}]},
        ]
        profile_iter = iter(profile_results)
        def _evaluate(expr: str) -> Any:
            calls.append(expr)
            if "document.readyState" in expr:
                return "complete"
            if "document.body ? document.body.innerHTML.length : 0" in expr:
                return 180
            if "EXTRACT_USER" in expr:
                return next(profile_iter)
            return None
        adapter.evaluate.side_effect = _evaluate

        page.navigate("https://www.xiaohongshu.com/user/profile/u123")
        page.wait_for_load()
        page.wait_dom_stable()
        user_data = page.evaluate("EXTRACT_USER_DATA_JS")
        notes_data = page.evaluate("EXTRACT_USER_NOTES_JS")

        self.assertEqual(user_data["nickname"], "Alice")
        self.assertEqual(len(notes_data["notes"]), 2)

    # --- feed_detail flow ---

    def test_feed_detail_scroll_and_interaction_flow(self) -> None:
        page, adapter = self._make_page()
        calls: list[str] = []
        def _evaluate(expr: str) -> Any:
            calls.append(expr)
            if "document.readyState" in expr:
                return "complete"
            if "document.body ? document.body.innerHTML.length : 0" in expr:
                return 220
            if "EXTRACT_DETAIL_JS" in expr:
                return {"note_id": "nd1", "title": "Hello"}
            if "pageYOffset" in expr or "scrollTop" in expr:
                return 900 if calls.count(expr) > 1 else 100
            if "innerHeight" in expr:
                return 800
            if "querySelectorAll" in expr and "?.click()" in expr:
                return True
            return None
        adapter.evaluate.side_effect = _evaluate
        adapter.get_current_url.return_value = "https://www.xiaohongshu.com"

        page.navigate("https://www.xiaohongshu.com/discovery/item/nd1")
        page.wait_for_load()
        page.wait_dom_stable()
        detail = page.evaluate("EXTRACT_DETAIL_JS")

        before_top = page.get_scroll_top()
        viewport_height = page.get_viewport_height()
        page.scroll_by(0, 400)
        page.scroll_to_bottom()
        page.scroll_element_into_view(".comments-container")
        page.dispatch_wheel_event(100)
        count = page.get_elements_count(".parent-comment")
        page.scroll_nth_element_into_view(".parent-comment", count - 1)
        clicked = page.evaluate('document.querySelectorAll(".show-more")[0]?.click()')

        self.assertEqual(detail["note_id"], "nd1")
        self.assertEqual(before_top, 100)
        self.assertEqual(viewport_height, 800)
        self.assertTrue(clicked)

    # --- comment flow ---

    def test_comment_post_flow(self) -> None:
        page, adapter = self._make_page()
        calls: list[str] = []
        def _evaluate(expr: str) -> Any:
            calls.append(expr)
            if "document.readyState" in expr:
                return "complete"
            if "document.body ? document.body.innerHTML.length : 0" in expr:
                return 160
            return True
        adapter.evaluate.side_effect = _evaluate
        adapter.get_current_url.return_value = "https://www.xiaohongshu.com"

        page.navigate("https://www.xiaohongshu.com/discovery/item/nd1")
        page.wait_for_load()
        page.wait_dom_stable()
        has_trigger = page.has_element(".comment-input-trigger")
        page.click_element(".comment-input-trigger")
        page.wait_for_element(".comment-input-field", timeout=2.0)
        page.input_content_editable(".comment-input-field", "Great post!")
        page.click_element(".comment-submit-button")

        self.assertTrue(has_trigger)

    # --- like_favorite flow ---

    def test_like_button_click_flow(self) -> None:
        page, adapter = self._make_page()
        calls: list[str] = []
        def _evaluate(expr: str) -> Any:
            calls.append(expr)
            if "document.readyState" in expr:
                return "complete"
            if "document.body ? document.body.innerHTML.length : 0" in expr:
                return 140
            if "GET_INTERACT_STATE_JS" in expr:
                return {"liked": False, "collected": False}
            if ".click()" in expr:
                return True
            return None
        adapter.evaluate.side_effect = _evaluate

        state = page.evaluate("GET_INTERACT_STATE_JS")
        page.navigate("https://www.xiaohongshu.com/discovery/item/nd1")
        page.wait_for_load()
        page.wait_dom_stable()
        page.click_element(".like-button")

        self.assertFalse(state["liked"])
        adapter.open_url.assert_called_once()


if __name__ == "__main__":
    unittest.main()

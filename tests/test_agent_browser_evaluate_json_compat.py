from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from xhs import feed_detail, feeds, like_favorite, search, user_profile


_SAMPLE_FEED = {
    "id": "feed-1",
    "xsecToken": "token-1",
    "modelType": "note",
    "noteCard": {
        "displayTitle": "第一条笔记",
        "type": "normal",
        "user": {"userId": "user-1", "nickname": "测试用户"},
    },
}


class AgentBrowserEvaluateJsonCompatTest(unittest.TestCase):
    def test_list_feeds_accepts_predecoded_eval_payload(self) -> None:
        page = mock.Mock()
        page.evaluate.return_value = [_SAMPLE_FEED]

        result = feeds.list_feeds(page)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "feed-1")
        self.assertEqual(result[0].note_card.display_title, "第一条笔记")

    def test_search_feeds_accepts_predecoded_eval_payload(self) -> None:
        page = mock.Mock()
        page.evaluate.side_effect = [True, [_SAMPLE_FEED]]

        result = search.search_feeds(page, keyword="测试关键词")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "feed-1")
        self.assertEqual(result[0].xsec_token, "token-1")

    def test_extract_feed_detail_accepts_predecoded_eval_payload(self) -> None:
        page = mock.Mock()
        page.evaluate.return_value = {
            "feed-1": {
                "note": {
                    "noteId": "feed-1",
                    "title": "详情标题",
                    "interactInfo": {"liked": True, "collected": False},
                },
                "comments": {"list": [{"id": "comment-1", "content": "好看"}]},
            }
        }

        result = feed_detail._extract_feed_detail(page, "feed-1")

        self.assertEqual(result.note.note_id, "feed-1")
        self.assertEqual(result.note.title, "详情标题")
        self.assertEqual(len(result.comments.list_), 1)
        self.assertEqual(result.comments.list_[0].content, "好看")

    def test_get_interact_state_accepts_predecoded_eval_payload(self) -> None:
        page = mock.Mock()
        page.evaluate.return_value = {
            "feed-1": {
                "note": {
                    "interactInfo": {
                        "liked": True,
                        "collected": False,
                    }
                }
            }
        }

        liked, collected = like_favorite._get_interact_state(page, "feed-1")

        self.assertTrue(liked)
        self.assertFalse(collected)

    def test_extract_user_profile_data_accepts_predecoded_eval_payload(self) -> None:
        page = mock.Mock()
        page.evaluate.side_effect = [
            True,
            {
                "basicInfo": {"nickname": "测试主页", "redId": "red-1"},
                "interactions": [{"type": "fans", "name": "粉丝", "count": "88"}],
            },
            [[_SAMPLE_FEED]],
        ]

        result = user_profile._extract_user_profile_data(page)

        self.assertEqual(result.user_basic_info.nickname, "测试主页")
        self.assertEqual(result.user_basic_info.red_id, "red-1")
        self.assertEqual(len(result.interactions), 1)
        self.assertEqual(result.interactions[0].count, "88")
        self.assertEqual(len(result.feeds), 1)
        self.assertEqual(result.feeds[0].id, "feed-1")


if __name__ == "__main__":
    unittest.main()

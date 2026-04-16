from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from xhs import publish_long_article
from xhs.errors import PublishError


class AgentBrowserPublishLongArticleTest(unittest.TestCase):
    def test_fill_long_title_raises_when_eval_reports_missing_element(self) -> None:
        page = mock.Mock()
        page.evaluate.return_value = False

        with self.assertRaises(PublishError):
            publish_long_article._fill_long_title(page, "长文标题")

        page.wait_for_element.assert_called_once_with(publish_long_article.LONG_ARTICLE_TITLE, timeout=10)
        page.evaluate.assert_called_once()

    def test_insert_images_to_editor_raises_when_eval_reports_failure(self) -> None:
        page = mock.Mock()
        page.evaluate.return_value = False

        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "cover.png"
            image_path.write_bytes(b"png")

            with self.assertRaises(PublishError):
                publish_long_article._insert_images_to_editor(page, [str(image_path)])

        page.evaluate.assert_called_once()
        expression = page.evaluate.call_args.args[0]
        self.assertIn(image_path.resolve().as_uri(), expression)


if __name__ == "__main__":
    unittest.main()

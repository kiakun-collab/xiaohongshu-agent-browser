from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from xhs import publish, publish_video
from xhs.errors import ElementNotFoundError, PublishError
from xhs.selectors import FILE_INPUT, UPLOAD_INPUT


class AgentBrowserUploadFallbackTest(unittest.TestCase):
    def test_upload_images_falls_back_to_generic_file_input_when_drag_drop_target_fails(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png") as image_file:
            page = mock.Mock()
            page.set_file_input.side_effect = [ElementNotFoundError(UPLOAD_INPUT), None]

            with (
                mock.patch("xhs.publish._wait_for_upload_complete") as mock_wait,
                mock.patch("xhs.publish.time.sleep"),
            ):
                publish._upload_images(page, [image_file.name])

        self.assertEqual(
            page.set_file_input.call_args_list,
            [
                mock.call(UPLOAD_INPUT, [image_file.name]),
                mock.call(FILE_INPUT, [image_file.name]),
            ],
        )
        mock_wait.assert_called_once_with(page, 1)

    def test_upload_images_raises_publish_error_when_all_upload_targets_fail(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png") as image_file:
            page = mock.Mock()
            page.set_file_input.side_effect = [ElementNotFoundError(UPLOAD_INPUT), ElementNotFoundError(FILE_INPUT)]

            with self.assertRaises(PublishError) as ctx:
                publish._upload_images(page, [image_file.name])

        self.assertIn(UPLOAD_INPUT, str(ctx.exception))
        self.assertIn(FILE_INPUT, str(ctx.exception))
        self.assertEqual(
            page.set_file_input.call_args_list,
            [
                mock.call(UPLOAD_INPUT, [image_file.name]),
                mock.call(FILE_INPUT, [image_file.name]),
            ],
        )

    def test_upload_video_falls_back_to_generic_file_input_when_drag_drop_target_fails(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as video_file:
            page = mock.Mock()
            page.has_element.return_value = True
            page.set_file_input.side_effect = [ElementNotFoundError(UPLOAD_INPUT), None]

            with mock.patch("xhs.publish_video._wait_for_publish_button_clickable") as mock_wait:
                publish_video._upload_video(page, video_file.name)

        page.has_element.assert_called_once_with(UPLOAD_INPUT)
        self.assertEqual(
            page.set_file_input.call_args_list,
            [
                mock.call(UPLOAD_INPUT, [video_file.name]),
                mock.call(FILE_INPUT, [video_file.name]),
            ],
        )
        mock_wait.assert_called_once_with(page)


if __name__ == "__main__":
    unittest.main()

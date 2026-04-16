from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import publish_pipeline


class AgentBrowserPublishPipelineTest(unittest.TestCase):
    def test_run_publish_pipeline_uses_agent_browser_backend_without_cdp_http_probe(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True

        with (
            mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False),
            mock.patch("publish_pipeline.get_profile_dir", return_value="/tmp/xhs-profile"),
            mock.patch("publish_pipeline.ensure_chrome", return_value=True),
            mock.patch("publish_pipeline.check_login_status", return_value=True),
            mock.patch("publish_pipeline.publish_image_content") as mock_publish,
            mock.patch("xhs.cdp.get_browser_backend", create=True, return_value="agent-browser"),
            mock.patch("xhs.cdp.get_agent_browser_adapter", create=True, return_value=adapter),
            mock.patch("xhs.cdp.requests.get", side_effect=AssertionError("should not probe CDP HTTP endpoint")),
        ):
            result = publish_pipeline.run_publish_pipeline(title="测试标题", content="测试正文")

        self.assertTrue(result["success"])
        mock_publish.assert_called_once()
        self.assertGreaterEqual(adapter.ensure_ready.call_count, 2)
        adapter.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

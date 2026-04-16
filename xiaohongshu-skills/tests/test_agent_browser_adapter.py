from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import chrome_launcher
from browser_adapter import AgentBrowserAdapter, SnapshotElement


class AgentBrowserAdapterTest(unittest.TestCase):
    def test_parse_snapshot_line_normalizes_ref_and_text(self) -> None:
        line = '  - button "发布" [disabled] [ref=e12]'

        element = AgentBrowserAdapter._parse_snapshot_line(line)

        self.assertEqual(
            element,
            SnapshotElement(role="button", text="发布", ref="@e12", raw=line),
        )

    def test_get_snapshot_returns_only_parsed_interactive_elements(self) -> None:
        adapter = AgentBrowserAdapter(agent_browser_path="agent-browser")
        output = '\n'.join(
            [
                'RootWebArea "首页"',
                '  - button "发布" [ref=@e12]',
                '  - textbox "搜索" [ref=e18]',
                '  - generic',
            ]
        )

        with mock.patch.object(adapter, "_run_command", return_value={"success": True, "output": output}):
            elements = adapter.get_snapshot(interactive_only=True)

        self.assertEqual(
            elements,
            [
                SnapshotElement(role="button", text="发布", ref="@e12", raw='  - button "发布" [ref=@e12]'),
                SnapshotElement(role="textbox", text="搜索", ref="@e18", raw='  - textbox "搜索" [ref=e18]'),
            ],
        )

    def test_ensure_ready_opens_blank_page_when_session_is_missing(self) -> None:
        adapter = AgentBrowserAdapter(
            agent_browser_path="agent-browser",
            session_name="xiaohongshu",
            profile_dir="/tmp/xhs-profile",
            headed=True,
            launch_args=("--no-sandbox", "--disable-dev-shm-usage"),
        )
        run_results = [
            {"success": False, "output": "", "error": "no active page"},
            {"success": True, "output": "", "error": ""},
        ]

        with mock.patch.object(adapter, "_run_command", side_effect=run_results) as mock_run:
            ready = adapter.ensure_ready()

        self.assertTrue(ready)
        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(mock_run.call_args_list[0].args, ("get", "url"))
        self.assertEqual(
            mock_run.call_args_list[1].args,
            ("open", "about:blank"),
        )
        self.assertEqual(
            mock_run.call_args_list[1].kwargs,
            {"include_launch_args": True},
        )


class ChromeLauncherBackendSelectionTest(unittest.TestCase):
    def test_ensure_chrome_uses_agent_browser_backend_when_enabled(self) -> None:
        adapter = mock.Mock()
        adapter.ensure_ready.return_value = True

        with mock.patch.dict(os.environ, {"XHS_BROWSER_BACKEND": "agent-browser"}, clear=False), mock.patch.object(
            chrome_launcher,
            "get_agent_browser_adapter",
            return_value=adapter,
        ) as mock_get_adapter:
            ready = chrome_launcher.ensure_chrome(port=9333, headless=False, user_data_dir="/tmp/profile")

        self.assertTrue(ready)
        mock_get_adapter.assert_called_once_with(headless=False, user_data_dir="/tmp/profile")
        adapter.ensure_ready.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

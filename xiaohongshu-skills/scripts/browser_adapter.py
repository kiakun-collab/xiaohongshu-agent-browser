"""agent-browser CLI 适配层。"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_AGENT_BROWSER_PATH = "/home/ubuntu/agent-browser/bin/agent-browser-linux-x64"
DEFAULT_SESSION_NAME = "xiaohongshu"
DEFAULT_LAUNCH_ARGS = ("--no-sandbox",)


@dataclass(frozen=True)
class SnapshotElement:
    role: str
    text: str
    ref: str
    raw: str


class AgentBrowserAdapter:
    """将 `agent-browser` CLI 封装为可复用的浏览器适配器。"""

    def __init__(
        self,
        agent_browser_path: str | None = None,
        session_name: str | None = None,
        profile_dir: str | None = None,
        headed: bool | None = None,
        launch_args: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.agent_browser_path = agent_browser_path or self._resolve_agent_browser_path()
        self.session_name = session_name or os.getenv("XHS_AGENT_BROWSER_SESSION") or DEFAULT_SESSION_NAME
        self.profile_dir = profile_dir
        self.headed = headed
        self.launch_args = self._normalize_launch_args(launch_args)

    def ensure_ready(self) -> bool:
        """确保会话可用，不主动打断已有页面。"""
        if self.get_current_url():
            return True
        result = self._run_command("open", "about:blank", include_launch_args=True)
        return bool(result["success"])

    def open_url(self, url: str) -> bool:
        result = self._run_command("open", url, include_launch_args=True)
        return bool(result["success"])

    def get_current_url(self) -> str | None:
        result = self._run_command("get", "url")
        if not result["success"]:
            return None
        current_url = result["output"].strip()
        return current_url or None

    def get_snapshot(self, interactive_only: bool = True) -> list[SnapshotElement]:
        command: list[str] = ["snapshot"]
        if interactive_only:
            command.append("-i")
        result = self._run_command(*command)
        if not result["success"]:
            return []
        return self._parse_snapshot(result["output"])

    def click_element(self, ref: str) -> bool:
        result = self._run_command("click", self._normalize_ref(ref))
        return bool(result["success"])

    def fill_element(self, ref: str, text: str) -> bool:
        result = self._run_command("fill", self._normalize_ref(ref), text)
        return bool(result["success"])

    def take_screenshot(self, path: str) -> bool:
        result = self._run_command("screenshot", path)
        return bool(result["success"])

    def close(self, all_sessions: bool = False) -> bool:
        command = ["close"]
        if all_sessions:
            command.append("--all")
        result = self._run_command(*command)
        return bool(result["success"])

    def _run_command(self, *command_args: str, include_launch_args: bool = False) -> dict[str, Any]:
        command = self._build_command(*command_args, include_launch_args=include_launch_args)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"未找到 agent-browser，可通过 XHS_AGENT_BROWSER_BIN 指定路径: {self.agent_browser_path}"
            ) from exc

        if result.returncode != 0:
            logger.debug("agent-browser command failed: %s", result.stderr.strip())

        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "command": command,
        }

    def _build_command(self, *command_args: str, include_launch_args: bool = False) -> list[str]:
        command = [self.agent_browser_path]
        if self.session_name:
            command.extend(["--session", self.session_name])
        if self.profile_dir:
            command.extend(["--profile", self.profile_dir])
        if self.headed:
            command.append("--headed")
        if include_launch_args and self.launch_args:
            command.extend(["--args", ",".join(self.launch_args)])
        command.extend(command_args)
        return command

    @staticmethod
    def _resolve_agent_browser_path() -> str:
        env_path = os.getenv("XHS_AGENT_BROWSER_BIN")
        if env_path:
            return env_path
        resolved = shutil.which("agent-browser")
        if resolved:
            return resolved
        return DEFAULT_AGENT_BROWSER_PATH

    @staticmethod
    def _normalize_launch_args(launch_args: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
        if launch_args is not None:
            return tuple(arg for arg in launch_args if arg)

        env_args = os.getenv("XHS_AGENT_BROWSER_ARGS", "")
        if env_args.strip():
            return tuple(part.strip() for part in re.split(r"[,\n]", env_args) if part.strip())

        return DEFAULT_LAUNCH_ARGS

    @classmethod
    def _parse_snapshot(cls, output: str) -> list[SnapshotElement]:
        elements: list[SnapshotElement] = []
        for line in output.splitlines():
            element = cls._parse_snapshot_line(line)
            if element is not None:
                elements.append(element)
        return elements

    @staticmethod
    def _parse_snapshot_line(line: str) -> SnapshotElement | None:
        match = re.search(
            r'^\s*(?:[-*]\s+)?(?P<role>[\w-]+)(?:\s+"(?P<text>.*?)")?.*?\[ref=(?P<ref>@?[\w-]+)\]\s*$',
            line,
        )
        if not match:
            return None

        return SnapshotElement(
            role=match.group("role"),
            text=match.group("text") or "",
            ref=AgentBrowserAdapter._normalize_ref(match.group("ref")),
            raw=line,
        )

    @staticmethod
    def _normalize_ref(ref: str) -> str:
        normalized = ref.strip()
        if normalized.startswith("@"):
            return normalized
        return f"@{normalized}"

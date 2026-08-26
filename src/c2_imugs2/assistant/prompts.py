"""Versioned prompt loading and LangChain prompt construction."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import re
from string import Formatter
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


_SAFE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class PromptConfigurationError(ValueError):
    """Raised when a prompt version is missing or has an invalid contract."""


@dataclass(frozen=True, slots=True)
class PromptBundle:
    version: str
    system: str
    mission_contract: str
    user_message: str
    structured_guidance: str

    def chat_prompt(self, *, structured_output: bool) -> ChatPromptTemplate:
        system = f"{self.system.rstrip()}\n\n{self.mission_contract.strip()}"
        if structured_output:
            system = f"{system.rstrip()}\n\n{self.structured_guidance.strip()}"
        return ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", self.user_message),
            ]
        )


class PromptCatalog:
    """Load editable prompts from ``prompt_templates/<version>``."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root

    def load(self, version: str) -> PromptBundle:
        if not _SAFE_VERSION.fullmatch(version):
            raise PromptConfigurationError(f"unsafe prompt version: {version!r}")

        if self._root is None:
            version_root: Any = (
                resources.files("c2_imugs2.assistant") / "prompt_templates" / version
            )
        else:
            version_root = self._root / version

        try:
            system = (version_root / "system.txt").read_text(encoding="utf-8")
            mission_contract = (version_root / "mission_contract.txt").read_text(
                encoding="utf-8"
            )
            user_message = (version_root / "user_message.txt").read_text(encoding="utf-8")
            structured = (version_root / "structured_output.txt").read_text(
                encoding="utf-8"
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            raise PromptConfigurationError(
                f"prompt version {version!r} is incomplete or missing"
            ) from exc

        required_user_fields = {
            "picture_revision",
            "picture_observed_at",
            "operational_picture_json",
            "user_message",
        }
        actual_user_fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(user_message)
            if field_name is not None
        }
        missing = required_user_fields - actual_user_fields
        if missing:
            raise PromptConfigurationError(
                "user prompt is missing required fields: " + ", ".join(sorted(missing))
            )
        if not system.strip() or not mission_contract.strip() or not structured.strip():
            raise PromptConfigurationError("prompt files cannot be empty")

        return PromptBundle(
            version=version,
            system=system.strip(),
            mission_contract=mission_contract.strip(),
            user_message=user_message.strip(),
            structured_guidance=structured.strip(),
        )

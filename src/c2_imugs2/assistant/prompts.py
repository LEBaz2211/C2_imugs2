"""Versioned prompt loading and LangChain prompt construction."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
from string import Formatter
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


_SAFE_VERSION_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_MANIFEST_NAME = "prompt.json"


class PromptConfigurationError(ValueError):
    """Raised when a prompt version is missing or has an invalid contract."""


@dataclass(frozen=True, slots=True)
class PromptBundle:
    version: str
    system: str
    mission_contract: str
    examples: str
    user_message: str
    structured_guidance: str

    def chat_prompt(self, *, structured_output: bool) -> ChatPromptTemplate:
        system = f"{self.system.rstrip()}\n\n{self.mission_contract.strip()}"
        if self.examples:
            system = f"{system.rstrip()}\n\n{self.examples.strip()}"
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
    """Load immutable prompts by flat or family-qualified version ID.

    Historical flat versions use the original four-file layout. New releases
    may use ``<family>/<version>/prompt.json`` to compose ordered sections and
    examples without adding another hard-coded file to this loader.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root

    def load(self, version: str) -> PromptBundle:
        version_parts = self._safe_parts(version, label="prompt version")

        if self._root is None:
            version_root: Any = resources.files("c2_imugs2.assistant") / "prompt_templates"
        else:
            version_root = self._root
        for part in version_parts:
            version_root = version_root / part

        try:
            manifest_path = version_root / _MANIFEST_NAME
            if manifest_path.is_file():
                loaded = self._load_manifest_version(version, version_root, manifest_path)
            else:
                loaded = self._load_legacy_version(version_root)
        except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError) as exc:
            raise PromptConfigurationError(
                f"prompt version {version!r} is incomplete or missing"
            ) from exc

        system, mission_contract, examples, user_message, structured = loaded

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
            examples=examples.strip(),
            user_message=user_message.strip(),
            structured_guidance=structured.strip(),
        )

    def _load_legacy_version(self, version_root: Any) -> tuple[str, str, str, str, str]:
        return (
            (version_root / "system.txt").read_text(encoding="utf-8"),
            (version_root / "mission_contract.txt").read_text(encoding="utf-8"),
            "",
            (version_root / "user_message.txt").read_text(encoding="utf-8"),
            (version_root / "structured_output.txt").read_text(encoding="utf-8"),
        )

    def _load_manifest_version(
        self,
        version: str,
        version_root: Any,
        manifest_path: Any,
    ) -> tuple[str, str, str, str, str]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise PromptConfigurationError(
                f"prompt version {version!r} has an unsupported manifest"
            )
        if manifest.get("version") != version:
            raise PromptConfigurationError(
                f"prompt manifest version must equal {version!r}"
            )

        system_files = manifest.get("system")
        example_files = manifest.get("examples", [])
        if not isinstance(system_files, list) or not system_files:
            raise PromptConfigurationError("prompt manifest system must be a non-empty list")
        if not isinstance(example_files, list):
            raise PromptConfigurationError("prompt manifest examples must be a list")

        system = self._read_sections(version_root, system_files, "system")
        examples = self._read_sections(version_root, example_files, "examples")
        mission_contract = self._read_component(
            version_root, manifest.get("mission_contract"), "mission_contract"
        )
        user_message = self._read_component(
            version_root, manifest.get("user_message"), "user_message"
        )
        structured = self._read_component(
            version_root, manifest.get("structured_output"), "structured_output"
        )
        return system, mission_contract, examples, user_message, structured

    def _read_sections(self, root: Any, values: list[Any], label: str) -> str:
        return "\n\n".join(
            self._read_component(root, value, f"{label}[{index}]").strip()
            for index, value in enumerate(values)
        )

    def _read_component(self, root: Any, value: Any, label: str) -> str:
        if not isinstance(value, str):
            raise PromptConfigurationError(f"prompt manifest {label} must be a path")
        parts = self._safe_parts(value, label=f"prompt manifest {label}")
        component = root
        for part in parts:
            component = component / part
        return component.read_text(encoding="utf-8")

    @staticmethod
    def _safe_parts(value: str, *, label: str) -> tuple[str, ...]:
        if not isinstance(value, str) or not value:
            raise PromptConfigurationError(f"unsafe {label}: {value!r}")
        path = PurePosixPath(value)
        parts = path.parts
        if (
            path.is_absolute()
            or not parts
            or any(part in {".", ".."} for part in parts)
            or any(not _SAFE_VERSION_SEGMENT.fullmatch(part) for part in parts)
        ):
            raise PromptConfigurationError(f"unsafe {label}: {value!r}")
        return parts

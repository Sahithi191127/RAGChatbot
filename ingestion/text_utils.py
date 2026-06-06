"""Shared text parsing helpers for markdown and HTML extraction."""

from __future__ import annotations

import re

from ingestion.models import ManagerBlock

_MANAGER_NAME_RE = re.compile(
    r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+(?:\s+[A-Z]\.?\s*[A-Z]\.?)?$"
)
_INITIALS_RE = re.compile(r"^[A-Z]{1,3}$")
_TENURE_RE = re.compile(
    r"([A-Za-z]{3,9}\s+\d{4})\s*\\?-\s*(Present|[A-Za-z]{3,9}\s+\d{4})",
    re.IGNORECASE,
)


def normalize_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in text.split("\n")]


def _skip_blank(section_lines: list[str], index: int) -> int:
    while index < len(section_lines) and not section_lines[index].strip():
        index += 1
    return index


def parse_manager_blocks(section_lines: list[str]) -> list[ManagerBlock]:
    managers: list[ManagerBlock] = []
    index = 0
    while index < len(section_lines):
        line = section_lines[index]
        if line in ("### Fund management", "###") or line == "View details":
            index += 1
            continue
        if not line:
            index += 1
            continue
        if _INITIALS_RE.match(line):
            index += 1
            index = _skip_blank(section_lines, index)
            if index >= len(section_lines):
                break
            name_line = section_lines[index]
            if not _MANAGER_NAME_RE.match(name_line):
                index += 1
                continue
            name = name_line
            index += 1
            index = _skip_blank(section_lines, index)
            tenure = ""
            if index < len(section_lines):
                tenure_line = section_lines[index]
                if _TENURE_RE.search(tenure_line) or "Present" in tenure_line:
                    tenure = tenure_line.replace("\\", "")
                    index += 1

            education = ""
            experience = ""
            also_manages: list[str] = []
            while index < len(section_lines):
                index = _skip_blank(section_lines, index)
                if index >= len(section_lines):
                    break
                current = section_lines[index]
                if _INITIALS_RE.match(current) or current.startswith("### "):
                    break
                if current == "Education" and index + 1 < len(section_lines):
                    index += 1
                    index = _skip_blank(section_lines, index)
                    if index < len(section_lines):
                        education = section_lines[index]
                elif current == "Experience" and index + 1 < len(section_lines):
                    index += 1
                    index = _skip_blank(section_lines, index)
                    if index < len(section_lines):
                        experience = section_lines[index]
                elif current == "Also manages these schemes":
                    index += 1
                    while index < len(section_lines):
                        scheme_line = section_lines[index]
                        if (
                            _INITIALS_RE.match(scheme_line)
                            or scheme_line.startswith("### ")
                            or scheme_line == "Education"
                        ):
                            break
                        if scheme_line and not scheme_line.startswith("["):
                            also_manages.append(scheme_line)
                        index += 1
                    continue
                index += 1

            text_parts = [f"{name} — Fund Manager, {tenure}".strip(", ")]
            if education:
                text_parts.append(f"Education: {education}")
            if experience:
                text_parts.append(f"Experience: {experience}")
            managers.append(
                ManagerBlock(
                    name=name,
                    tenure=tenure,
                    education=education,
                    experience=experience,
                    also_manages=also_manages,
                    text="\n".join(text_parts),
                )
            )
            continue
        if _MANAGER_NAME_RE.match(line):
            managers.append(ManagerBlock(name=line, text=line))
        index += 1

    return managers

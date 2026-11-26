"""Prompt file management and versioning for PEPTalk LLM tasks.

Finds prompt files matching prompts/<task>_v<n>.md and sorts versions numerically.
"""

import re
from pathlib import Path


def list_prompt_files(
    task: str, prompts_dir: Path | str = "prompts"
) -> list[tuple[int, str, Path]]:
    """Find all prompts/<task>_v<n>.md files sorted by integer version n."""
    dir_path = Path(prompts_dir)
    if not dir_path.is_dir():
        return []

    pattern = re.compile(rf"^{re.escape(task)}_v(\d+)\.md$")
    matches: list[tuple[int, str, Path]] = []
    for file in dir_path.iterdir():
        if not file.is_file():
            continue
        m = pattern.match(file.name)
        if m:
            version_num = int(m.group(1))
            version_str = f"v{version_num}"
            matches.append((version_num, version_str, file))

    matches.sort(key=lambda item: item[0])
    return matches


def list_versions(task: str, prompts_dir: Path | str = "prompts") -> list[str]:
    """Return sorted version names like ['v1', 'v2', 'v3']."""
    return [version_str for _, version_str, _ in list_prompt_files(task, prompts_dir)]


def load_prompt(
    task: str,
    version: str | int | None = None,
    prompts_dir: Path | str = "prompts",
) -> tuple[str, str]:
    """Load prompt content and version string for a task.

    If version is None, loads the latest version.
    Returns (prompt_text, version_str).
    """
    files = list_prompt_files(task, prompts_dir)
    if not files:
        raise FileNotFoundError(f"No prompt templates found for task '{task}' in {prompts_dir}")

    if version is None:
        _, ver_str, path = files[-1]
        return path.read_text(encoding="utf-8").strip(), ver_str

    target_num = int(version.lstrip("vV")) if isinstance(version, str) else version
    for num, ver_str, path in files:
        if num == target_num:
            return path.read_text(encoding="utf-8").strip(), ver_str

    raise FileNotFoundError(
        f"Prompt version '{version}' not found for task '{task}' in {prompts_dir}"
    )

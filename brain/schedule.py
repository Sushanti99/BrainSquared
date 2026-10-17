"""Run `brain daily` every morning with macOS launchd, so todos are ready on wake.

If the Mac is asleep at the scheduled time, launchd runs the job when it wakes.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "so.brainsquared.daily"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = Path.home() / "Library" / "Logs" / "BrainSquared"


def plist_path() -> Path:
    return LAUNCH_AGENTS_DIR / f"{LABEL}.plist"


def parse_time(value: str) -> tuple[int, int]:
    hour_text, _, minute_text = value.partition(":")
    try:
        hour, minute = int(hour_text), int(minute_text or 0)
    except ValueError:
        raise ValueError(f"Use HH:MM for the time, got {value!r}.") from None
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"Use HH:MM for the time, got {value!r}.")
    return hour, minute


def build_plist(vault: Path, *, hour: int, minute: int) -> dict:
    return {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, "-m", "brain.cli", "daily", "--vault", str(vault)],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        # launchd starts jobs with a bare PATH; keep the user's so the agent CLIs resolve.
        "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        "StandardOutPath": str(LOG_DIR / "daily.log"),
        "StandardErrorPath": str(LOG_DIR / "daily.log"),
    }


def _launchctl(*args: str) -> None:
    subprocess.run(["/bin/launchctl", *args], capture_output=True, check=False)


def install(vault: Path, *, hour: int, minute: int, load: bool = True) -> Path:
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(build_plist(vault, hour=hour, minute=minute), handle)
    if load:
        domain = f"gui/{os.getuid()}"
        _launchctl("bootout", domain, str(path))  # replace any earlier schedule
        _launchctl("bootstrap", domain, str(path))
    return path


def remove(*, unload: bool = True) -> bool:
    path = plist_path()
    if not path.exists():
        return False
    if unload:
        _launchctl("bootout", f"gui/{os.getuid()}", str(path))
    path.unlink()
    return True

import plistlib

import pytest

from brain import schedule


def test_install_and_remove_write_a_launchd_job(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "LAUNCH_AGENTS_DIR", tmp_path / "LaunchAgents")
    monkeypatch.setattr(schedule, "LOG_DIR", tmp_path / "logs")

    path = schedule.install(tmp_path / "vault", hour=6, minute=30, load=False)

    job = plistlib.loads(path.read_bytes())
    assert job["Label"] == schedule.LABEL
    assert job["ProgramArguments"][-4:] == ["brain.cli", "daily", "--vault", str(tmp_path / "vault")]
    assert job["StartCalendarInterval"] == {"Hour": 6, "Minute": 30}
    assert schedule.remove(unload=False) is True
    assert schedule.remove(unload=False) is False


def test_parse_time():
    assert schedule.parse_time("07:05") == (7, 5)
    for bad in ("25:00", "7:61", "soon"):
        with pytest.raises(ValueError):
            schedule.parse_time(bad)

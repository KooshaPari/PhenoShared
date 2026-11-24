"""Integration tests for bench.energy measurement module."""

from unittest.mock import patch

from bench.energy import (
    EnergySource,
    _NoOpSource,
    _parse_powermetrics_line,
    detect_source,
)


def test_energypowermetrics_has_value():
    assert EnergySource.POWERMETRICS.value == "powermetrics"


def test_detect_source_prefers_nvidia_smi():
    result = detect_source(prefer=EnergySource.NVIDIA_SMI)
    assert result == EnergySource.NVIDIA_SMI


def test_detect_source_none_returns_none_on_macos_without_powermetrics():
    with (
        patch("bench.energy.platform") as mock_platform,
        patch("bench.energy.shutil.which", return_value=None),
    ):
        mock_platform.system.return_value = "darwin"
        result = detect_source(prefer=EnergySource.NONE)
        assert result == EnergySource.NONE


def test_parse_powermetrics_line():
    line = b"CPU Power: 1234 mW\nGPU Power: 5678 mW\nANE Power: 901 mW"
    result = _parse_powermetrics_line(line)
    assert result == 1234 + 5678 + 901


def test_parse_powermetrics_line_no_power():
    line = b"Some other line: 100 units\n"
    result = _parse_powermetrics_line(line)
    assert result == 0.0


def test_noop_source_start_stop_no_raise():
    src = _NoOpSource()
    src.start()
    total = src.stop()
    assert total.joules == 0.0
    assert total.samples == 0
    assert total.source == EnergySource.NONE

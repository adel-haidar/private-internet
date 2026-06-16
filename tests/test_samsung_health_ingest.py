"""
Tests for the Samsung Health JSON ingest parser.

Verifies that parse_samsung_health_export correctly maps the Samsung Health
daily_summary schema to HealthMetric rows using the same metric_type vocabulary
and units as the Apple Health pipeline.

Also verifies is_samsung_health_json correctly distinguishes Samsung exports
from Apple XML, random JSON, and garbage bytes.
"""
import json
from datetime import timezone

import pytest

from assistant.health.ingest import is_samsung_health_json, parse_samsung_health_export
from assistant.health.models import HealthMetric


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_EXPORT = {
    "user_info": {
        "name": "Yuki",
        "device": "Galaxy Watch6",
        "export_date": "2026-06-16 17:48:44",
    },
    "daily_summary": [
        {
            "date": "2026-06-14",
            "step_count": 8432,
            "calories_kcal": 2150,
            "heart_rate_avg": 72,
            "sleep_duration_min": 420,
        },
        {
            "date": "2026-06-15",
            "step_count": 9120,
            "calories_kcal": 2280,
            "heart_rate_avg": 75,
            "sleep_duration_min": 390,
        },
        {
            "date": "2026-06-16",
            "step_count": 6500,
            "calories_kcal": 1900,
            "heart_rate_avg": 70,
            "sleep_duration_min": 450,
        },
    ],
}


def _to_bytes(obj: dict) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _metrics_by_type(metrics: list[HealthMetric]) -> dict[str, list[HealthMetric]]:
    result: dict[str, list[HealthMetric]] = {}
    for m in metrics:
        result.setdefault(m.metric_type, []).append(m)
    return result


# ── is_samsung_health_json ────────────────────────────────────────────────────

class TestIsSamsungHealthJson:
    def test_valid_export_returns_true(self):
        assert is_samsung_health_json(_to_bytes(SAMPLE_EXPORT)) is True

    def test_plain_json_without_daily_summary_returns_false(self):
        assert is_samsung_health_json(b'{"foo": "bar"}') is False

    def test_xml_bytes_returns_false(self):
        xml = b'<?xml version="1.0"?><HealthData/>'
        assert is_samsung_health_json(xml) is False

    def test_garbage_bytes_returns_false(self):
        assert is_samsung_health_json(b'\x00\x01\x02\x03') is False

    def test_empty_bytes_returns_false(self):
        assert is_samsung_health_json(b'') is False

    def test_json_array_root_returns_false(self):
        assert is_samsung_health_json(b'[1, 2, 3]') is False

    def test_minimal_valid_structure(self):
        minimal = {"daily_summary": []}
        assert is_samsung_health_json(_to_bytes(minimal)) is True


# ── parse_samsung_health_export — basics ──────────────────────────────────────

class TestParseSamsungHealthExport:
    def test_parses_sample_file(self):
        """Verify real sample file structure produces expected metric count."""
        with open("/home/adel/Downloads/samsung_health_export.json", "rb") as f:
            raw = f.read()
        metrics = parse_samsung_health_export(raw)
        # 3 days × 4 fields + 3 sleep_score = 15
        assert len(metrics) == 15

    def test_correct_metric_types_produced(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        assert set(by_type.keys()) == {
            "steps", "active_energy_kcal", "resting_hr",
            "sleep_duration_min", "sleep_score",
        }

    def test_three_rows_per_metric_type(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        for mtype in ("steps", "active_energy_kcal", "resting_hr", "sleep_duration_min", "sleep_score"):
            assert len(by_type[mtype]) == 3, f"Expected 3 rows for {mtype}"

    def test_all_source_is_samsung_health(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        assert all(m.source == "samsung_health" for m in metrics)

    def test_steps_values(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        step_values = sorted(m.value for m in by_type["steps"])
        assert step_values == [6500, 8432, 9120]

    def test_steps_unit(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        assert all(m.unit == "count" for m in by_type["steps"])

    def test_calories_values(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        cal_values = sorted(m.value for m in by_type["active_energy_kcal"])
        assert cal_values == [1900.0, 2150.0, 2280.0]

    def test_calories_unit(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        assert all(m.unit == "kcal" for m in by_type["active_energy_kcal"])

    def test_heart_rate_values(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        hr_values = sorted(m.value for m in by_type["resting_hr"])
        assert hr_values == [70.0, 72.0, 75.0]

    def test_heart_rate_unit(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        assert all(m.unit == "count/min" for m in by_type["resting_hr"])

    def test_sleep_values(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        sleep_values = sorted(m.value for m in by_type["sleep_duration_min"])
        assert sleep_values == [390.0, 420.0, 450.0]

    def test_sleep_unit(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)
        assert all(m.unit == "min" for m in by_type["sleep_duration_min"])


# ── Sleep score derivation ────────────────────────────────────────────────────

class TestSleepScoreDerivation:
    def test_sleep_score_derived_from_sleep_duration(self):
        """Sleep score = min(100, duration_min / 480 * 100)."""
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        by_type = _metrics_by_type(metrics)

        sleep_map = {m.recorded_at.date().isoformat(): m.value for m in by_type["sleep_duration_min"]}
        score_map = {m.recorded_at.date().isoformat(): m.value for m in by_type["sleep_score"]}

        for date_str, dur in sleep_map.items():
            expected = round(min(100.0, (dur / 480.0) * 100.0), 1)
            assert score_map[date_str] == pytest.approx(expected, abs=0.05), \
                f"Sleep score mismatch for {date_str}: expected {expected}, got {score_map[date_str]}"

    def test_sleep_score_capped_at_100(self):
        export = {
            "daily_summary": [{"date": "2026-01-01", "sleep_duration_min": 600}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        assert by_type["sleep_score"][0].value == 100.0

    def test_no_sleep_score_when_no_sleep_data(self):
        export = {
            "daily_summary": [{"date": "2026-01-01", "step_count": 5000}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        assert "sleep_score" not in by_type


# ── Timestamps ────────────────────────────────────────────────────────────────

class TestTimestamps:
    def test_recorded_at_is_noon_utc(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        for m in metrics:
            assert m.recorded_at.hour == 12
            assert m.recorded_at.minute == 0
            assert m.recorded_at.tzinfo == timezone.utc

    def test_dates_match_daily_summary(self):
        metrics = parse_samsung_health_export(_to_bytes(SAMPLE_EXPORT))
        dates = {m.recorded_at.date().isoformat() for m in metrics}
        assert dates == {"2026-06-14", "2026-06-15", "2026-06-16"}


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_daily_summary(self):
        export = {"daily_summary": []}
        assert parse_samsung_health_export(_to_bytes(export)) == []

    def test_missing_daily_summary_key(self):
        assert parse_samsung_health_export(b'{"user_info": {}}') == []

    def test_invalid_json_returns_empty(self):
        assert parse_samsung_health_export(b'not json at all') == []

    def test_row_with_missing_optional_fields(self):
        """A row with only some fields still produces metrics for present fields."""
        export = {
            "daily_summary": [{"date": "2026-01-01", "step_count": 7000}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        assert "steps" in by_type
        assert "active_energy_kcal" not in by_type
        assert "resting_hr" not in by_type

    def test_negative_values_are_skipped(self):
        export = {
            "daily_summary": [{"date": "2026-01-01", "step_count": -100, "calories_kcal": 2000}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        assert "steps" not in by_type
        assert "active_energy_kcal" in by_type

    def test_row_with_no_date_is_skipped(self):
        export = {
            "daily_summary": [{"step_count": 5000}]
        }
        assert parse_samsung_health_export(_to_bytes(export)) == []

    def test_row_with_bad_date_is_skipped(self):
        export = {
            "daily_summary": [{"date": "not-a-date", "step_count": 5000}]
        }
        assert parse_samsung_health_export(_to_bytes(export)) == []

    def test_future_optional_weight_field(self):
        """weight_kg is in _SH_FIELD_MAP — verify it maps correctly when present."""
        export = {
            "daily_summary": [{"date": "2026-01-01", "weight_kg": 82.5}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        assert "weight_kg" in by_type
        assert by_type["weight_kg"][0].unit == "kg"
        assert by_type["weight_kg"][0].value == pytest.approx(82.5)

    def test_non_numeric_value_is_skipped(self):
        export = {
            "daily_summary": [{"date": "2026-01-01", "step_count": "many", "calories_kcal": 2000}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        assert "steps" not in by_type
        assert "active_energy_kcal" in by_type

    def test_zero_sleep_does_not_produce_sleep_score(self):
        export = {
            "daily_summary": [{"date": "2026-01-01", "sleep_duration_min": 0}]
        }
        metrics = parse_samsung_health_export(_to_bytes(export))
        by_type = _metrics_by_type(metrics)
        # sleep_duration_min = 0 is skipped (value < 0 check only skips negatives;
        # zero IS inserted but should not produce a sleep_score since min is 0)
        # Confirm sleep_score is absent when duration is 0
        assert "sleep_score" not in by_type

import pandas as pd

from src.rules import night_large, pass_through, structuring, velocity


def frame(rows):
    df = pd.DataFrame(rows, columns=["account_id", "timestamp", "amount_kes", "txn_type"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def test_structuring_needs_three_deposits_near_threshold():
    rows = [("A", f"2026-03-01 1{i}:00", 95_000, "deposit") for i in range(3)]
    assert structuring(frame(rows)).sum() == 1  # only the third deposit completes the pattern
    assert structuring(frame(rows[:2])).sum() == 0


def test_structuring_ignores_amounts_well_below_band():
    rows = [("A", f"2026-03-01 1{i}:00", 40_000, "deposit") for i in range(5)]
    assert structuring(frame(rows)).sum() == 0


def test_structuring_is_per_account():
    rows = [(a, f"2026-03-01 1{i}:00", 95_000, "deposit") for i, a in enumerate("ABC")]
    assert structuring(frame(rows)).sum() == 0


def test_velocity_flags_burst_but_not_slow_activity():
    burst = [("A", f"2026-03-01 09:{m:02d}", 500, "transfer") for m in range(12)]
    slow = [("B", f"2026-03-01 {h:02d}:00", 500, "transfer") for h in range(8, 20)]
    out = velocity(frame(burst + slow))
    df = frame(burst + slow)
    assert out[df["account_id"] == "A"].any()
    assert not out[df["account_id"] == "B"].any()


def test_pass_through_catches_quick_exit():
    rows = [("A", "2026-03-01 10:00", 500_000, "deposit"), ("A", "2026-03-01 10:20", 480_000, "transfer")]
    assert pass_through(frame(rows)).tolist() == [False, True]


def test_pass_through_ignores_slow_exit():
    rows = [("A", "2026-03-01 10:00", 500_000, "deposit"), ("A", "2026-03-01 15:00", 480_000, "transfer")]
    assert not pass_through(frame(rows)).any()


def test_night_large_needs_repeat():
    one = [("A", "2026-03-01 02:00", 80_000, "transfer")]
    two = one + [("A", "2026-03-01 03:30", 90_000, "transfer")]
    assert not night_large(frame(one)).any()
    assert night_large(frame(two)).sum() == 1

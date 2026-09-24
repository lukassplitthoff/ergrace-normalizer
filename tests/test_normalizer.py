"""Physics and unit checks for ergrace.normalizer."""

import math

import numpy as np
import pytest

from ergrace import ERGNormalizer
from ergrace.normalizer import (C2_POWER_CONSTANT, power_from_distance_time,
                                power_from_speed, speed_from_power,
                                split_from_power, team_reference_power)

T_2K_MEN, T_2K_WOMEN = 334.7, 381.1     # 2000 m world records [s]
T_RELAY = 1800.0                         # 30 min [s]


# ── unit conversions ────────────────────────────────────────────────────────
def test_concept2_reference_points():
    # 2:00 /500 m <-> 202.5 W is the Concept2 textbook value
    assert power_from_distance_time(500, 120) == pytest.approx(202.546, rel=1e-4)
    assert split_from_power(202.546) == pytest.approx(120.0, rel=1e-5)
    # README numbers
    assert ERGNormalizer.time2power(340) == pytest.approx(569.92, abs=0.01)
    assert ERGNormalizer.time2power(400) == pytest.approx(350.00, abs=0.01)
    assert ERGNormalizer.distance2power(6000) == pytest.approx(350.0)


def test_speed_power_roundtrip():
    for p in (50.0, 202.5, 597.0, 1027.0):
        assert power_from_speed(speed_from_power(p)) == pytest.approx(p)


def test_world_record_powers_in_paper():
    assert ERGNormalizer.time2power(T_2K_MEN) == pytest.approx(597.4, abs=0.1)
    assert ERGNormalizer.time2power(T_2K_WOMEN) == pytest.approx(404.7, abs=0.1)


# ── team reference power ────────────────────────────────────────────────────
def test_reference_power_is_cube_root_mean():
    pm, pf = 597.4, 404.7
    expected = ((3 * pm ** (1 / 3) + 2 * pf ** (1 / 3)) / 5) ** 3
    assert team_reference_power([pm] * 3 + [pf] * 2) == pytest.approx(expected)
    # homogeneous team -> individual reference
    assert team_reference_power([pf] * 5) == pytest.approx(pf)
    # power-mean inequality: strictly below the arithmetic mean when mixed
    assert team_reference_power([pm, pf]) < (pm + pf) / 2


def test_reference_monotonic_in_number_of_men():
    n = ERGNormalizer.from_reference_times(2000, T_2K_MEN, T_2K_WOMEN, T_RELAY)
    refs = [n._calculate_ref_power(m, 5 - m) for m in range(6)]
    assert all(a < b for a, b in zip(refs, refs[1:]))


# ── scores ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("n_men", range(6))
def test_team_rowing_exactly_at_reference_scores_one(n_men):
    """Each rower at reference power for T/n -> score exactly 1 for any mix."""
    n_women = 5 - n_men
    norm = ERGNormalizer.from_reference_times(2000, T_2K_MEN, T_2K_WOMEN, T_RELAY)
    v_m = speed_from_power(norm.ref_power_men)
    v_f = speed_from_power(norm.ref_power_women)
    distance = T_RELAY / 5 * (n_men * v_m + n_women * v_f)   # distances add
    norm.add_team("ref", n_men, n_women, distance_m=distance).calculate_scores()
    d = norm.teams["ref"]
    assert d["score"] == pytest.approx(1.0, rel=1e-12)
    assert d["speed_score"] == pytest.approx(1.0, rel=1e-12)


def test_uniform_power_fraction_is_recovered():
    """Every rower at 70 % of reference power -> score 0.70 for any mix."""
    sigma = 0.70
    norm = ERGNormalizer.from_reference_times(2000, T_2K_MEN, T_2K_WOMEN, T_RELAY)
    for n_men in range(6):
        n_women = 5 - n_men
        v = (n_men * speed_from_power(sigma * norm.ref_power_men)
             + n_women * speed_from_power(sigma * norm.ref_power_women)) / 5
        norm.add_team(f"t{n_men}", n_men, n_women, distance_m=v * T_RELAY)
    norm.calculate_scores()
    for d in norm.teams.values():
        assert d["score"] == pytest.approx(sigma, rel=1e-12)


def test_score_is_power_ratio_and_cube_of_speed_score():
    norm = ERGNormalizer(597.4, 404.7, T_RELAY)
    norm.add_team("x", 3, 2, distance_m=9511).calculate_scores()
    d = norm.teams["x"]
    assert d["score"] == pytest.approx(d["actual_pwr"] / d["ref_pwr"])
    assert d["score"] == pytest.approx(d["speed_score"] ** 3)
    assert d["ref_distance_m"] == pytest.approx(9511 / d["speed_score"])


def test_drag_constant_cancels(monkeypatch):
    """Score must not depend on c when references are given as times."""
    import ergrace.normalizer as mod

    def score_with(c):
        monkeypatch.setattr(mod, "C2_POWER_CONSTANT", c)
        n = mod.ERGNormalizer.from_reference_times(2000, T_2K_MEN, T_2K_WOMEN, T_RELAY)
        n.add_team("x", 2, 3, distance_m=9268).calculate_scores()
        return n.teams["x"]["score"]

    assert score_with(2.8) == pytest.approx(score_with(3.7), rel=1e-12)
    monkeypatch.setattr(mod, "C2_POWER_CONSTANT", C2_POWER_CONSTANT)


def test_ranking_depends_only_on_power_ratio():
    """Scaling both reference powers by the same factor keeps the ranking."""
    teams = {"a": (3, 2, 9511), "b": (2, 3, 9268), "c": (0, 5, 8575)}

    def ranking(pm, pf):
        n = ERGNormalizer(pm, pf, T_RELAY)
        for k, (m, f, d) in teams.items():
            n.add_team(k, m, f, distance_m=d)
        return list(n.calculate_scores().get_results()["Team"])

    assert ranking(597.4, 404.7) == ranking(0.8 * 597.4, 0.8 * 404.7)


# ── API ─────────────────────────────────────────────────────────────────────
def test_backward_compatible_keyword():
    n = ERGNormalizer()
    n.add_team("old", 3, 2, distance_20min_m=6319)
    n.add_teams_from_dict({"older": {"n_men": 1, "n_women": 1,
                                     "distance_20min_m": 5000}})
    assert n.teams["old"]["distance_m"] == 6319
    assert n.teams["older"]["distance_m"] == 5000


@pytest.mark.parametrize("args", [(0, 0, 5000), (-1, 3, 5000), (2, 3, 0)])
def test_invalid_input(args):
    with pytest.raises(ValueError):
        ERGNormalizer().add_team("bad", *args[:2], distance_m=args[2])


def test_results_sorted_by_unrounded_score():
    n = ERGNormalizer.from_reference_times(2000, T_2K_MEN, T_2K_WOMEN, T_RELAY)
    n.add_team("CTH-GU", 3, 2, distance_m=9511)
    n.add_team("Chalmers 1", 2, 3, distance_m=9268)
    df = n.calculate_scores().get_results()
    assert list(df["Team"]) == ["Chalmers 1", "CTH-GU"]
    assert df["Score"].iloc[0] > df["Score"].iloc[1]
    assert math.isclose(df["Score"].iloc[0], df["Score"].iloc[1], rel_tol=1e-3)

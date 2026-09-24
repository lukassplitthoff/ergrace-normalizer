"""Physics and interface checks for RelayRace, MixedRace and References."""

import numpy as np
import pytest

from ergrace import MixedRace, References, RelayRace, format_time, parse_time

REFS = References(2000, {"Senior M": "5:34.7", "Senior W": "6:21.1",
                         "Junior M": "5:51.4", "Junior W": "6:40.2"})
V = {k: REFS.speed(k) for k in ("Senior M", "Senior W", "Junior M", "Junior W")}


# ── references & time helpers ───────────────────────────────────────────────
@pytest.mark.parametrize("label,key", [
    ("Senior M", ("senior", "M")), ("junior w", ("junior", "W")),
    ("Master F", ("master", "W")), ("M", ("senior", "M")), ("women junior", ("junior", "W"))])
def test_category_parsing(label, key):
    from ergrace.references import parse_category
    assert parse_category(label) == key


def test_unknown_category_raises():
    with pytest.raises(KeyError):
        REFS.speed("Master M")
    with pytest.raises(ValueError):
        REFS.speed("Senior X")


def test_time_helpers():
    assert parse_time("6:21.1") == pytest.approx(381.1)
    assert parse_time("1:02:03") == 3723
    assert parse_time(90) == 90
    assert format_time(381.1) == "6:21.1"
    assert format_time(3723, 0) == "1:02:03"
    assert format_time(-5.25, 1, sign=True) == "-0:05.2"


def test_default_references_senior_are_world_records():
    d = References.default()
    assert d.power("Senior M") == pytest.approx(597.4, abs=0.1)
    assert d.power("Senior W") == pytest.approx(404.7, abs=0.1)
    assert set(d.categories()) >= {"Junior M", "Master W"}


# ── relay physics ───────────────────────────────────────────────────────────
TEAM = ["Junior M", "Senior W", "Senior M"]


def _uniform(sigma, cats):
    return np.array([sigma ** (1 / 3) * V[c] for c in cats])


def test_relay_time_split_reference_is_arithmetic_mean():
    r = RelayRace(time="30:00", teams={"t": TEAM}, references=REFS)
    assert r.entries["t"]["ref_speed"] == pytest.approx(np.mean([V[c] for c in TEAM]))
    hc = r.handicaps()
    assert hc["Target Distance (m)"].iloc[0] == pytest.approx(1800 * np.mean([V[c] for c in TEAM]))


def test_relay_distance_split_reference_is_harmonic_mean():
    r = RelayRace(distance=3000, teams={"t": TEAM}, references=REFS)
    assert r.split == "distance"
    legs = sum(1000 / V[c] for c in TEAM)                 # times add
    assert r.handicaps()["Expected Time (s)"].iloc[0] == pytest.approx(legs)


@pytest.mark.parametrize("split", ["time", "distance"])
@pytest.mark.parametrize("sigma", [1.0, 0.63])
def test_relay_uniform_effort_recovered_fixed_time(split, sigma):
    T = 1800.0
    teams = {"a": TEAM, "b": ["Senior W"] * 3, "c": {"Senior M": 2, "Junior W": 1}}
    r = RelayRace(time=T, teams=teams, split=split, references=REFS)
    res = {}
    for name, cats in teams.items():
        cats = cats if isinstance(cats, list) else [k for k, n in cats.items() for _ in range(n)]
        v = _uniform(sigma, cats)
        if split == "time":
            res[name] = float(np.sum(v * T / len(v)))
        else:  # equal legs of length L: total time T = sum L/v  ->  D = n L
            L = T / np.sum(1 / v)
            res[name] = float(L * len(v))
    df = r.record(res).results()
    assert np.allclose(df["Score"], sigma, rtol=1e-12)


@pytest.mark.parametrize("split", ["time", "distance"])
def test_relay_uniform_effort_recovered_fixed_distance(split):
    D, sigma = 5000.0, 0.7
    r = RelayRace(distance=D, teams={"a": TEAM, "b": ["Junior W"] * 3},
                  split=split, references=REFS)
    res = {}
    for name, cats in (("a", TEAM), ("b", ["Junior W"] * 3)):
        v = _uniform(sigma, cats)
        res[name] = (float(np.sum(D / len(v) / v)) if split == "distance"
                     else float(D / np.mean(v)))
    df = r.record(res).results()
    assert np.allclose(df["Score"], sigma, rtol=1e-12)


def test_staggered_start_makes_everyone_arrive_together():
    level = 0.7
    teams = {"a": TEAM, "b": ["Senior W"] * 3, "c": ["Junior M", "Junior W", "Senior M"]}
    r = RelayRace(distance=3000, teams=teams, references=REFS, level=level)
    hc = r.handicaps()
    finish = hc["Start Offset (s)"] + hc["Expected Time (s)"]
    assert np.allclose(finish, finish.iloc[0])
    assert hc["Start Offset (s)"].min() == 0
    # rowing exactly at the level -> all within rounding of the common finish
    res = {n: t for n, t in zip(hc["Entry"], hc["Expected Time (s)"])}
    out = r.record(res).results()
    assert np.allclose(out["Vs Handicap (s)"], 0, atol=1e-9)
    assert np.allclose(out["Score"], level)


def test_time_race_credit_equalizes_at_level():
    r = RelayRace(time="20:00", teams={"a": TEAM, "b": ["Senior W"] * 3},
                  references=REFS, level=0.8)
    hc = r.handicaps()
    total = hc["Target Distance (m)"] + hc["Credit (m)"]
    assert np.allclose(total, total.iloc[0])


def test_relay_team_formats_and_errors():
    r = RelayRace(time=600, teams={"x": {"Senior M": 2, "Senior W": 1}}, references=REFS)
    assert r.entries["x"]["label"] == "2 Sen M + Sen W"
    with pytest.raises(ValueError):
        RelayRace(time=600, distance=2000)
    with pytest.raises(ValueError):
        RelayRace()
    with pytest.raises(KeyError):
        r.record({"nope": 3000})


# ── mixed race ──────────────────────────────────────────────────────────────
def test_mixed_individual_score_and_lookup_by_lane_or_name():
    race = MixedRace(distance=2000, references=REFS, lanes={
        1: ("Anna", "Junior W", "A"), 2: {"name": "Erik", "category": "Senior M", "team": "B"},
        3: "Senior W"})
    t_anna = 2000 / (0.6 ** (1 / 3) * V["Junior W"])
    race.record({1: t_anna, "Erik": "6:30.0", 3: "7:10.0"})
    df = race.results().set_index("Entry")
    assert df.loc["Anna", "Score"] == pytest.approx(0.6)
    assert df.loc["Erik", "Score"] == pytest.approx((2000 / 390 / V["Senior M"]) ** 3)
    assert df.loc["Lane 3", "Lane"] == 3
    teams = race.team_results()
    assert set(teams["Team"]) == {"A", "B"}


def test_mixed_time_race_distance_result():
    race = MixedRace(time="20:00", references=REFS, lanes={1: "Senior M", 2: "Junior W"})
    race.record({1: 1200 * V["Senior M"], 2: 1200 * V["Junior W"] * 0.9})
    df = race.results().set_index("Lane")
    assert df.loc[1, "Score"] == pytest.approx(1.0)
    assert df.loc[2, "Score"] == pytest.approx(0.9 ** 3)


def test_c_cancels_in_races(monkeypatch):
    import ergrace.normalizer as mod

    def score(c):
        monkeypatch.setattr(mod, "C2_POWER_CONSTANT", c)
        r = RelayRace(time=1800, teams={"a": TEAM}, references=REFS).record({"a": 9000})
        return r.results()["Score"].iloc[0]

    assert score(2.8) == pytest.approx(score(5.0), rel=1e-12)


def test_plots_render(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    r = RelayRace(distance=2000, teams={"a": TEAM, "b": ["Senior W"] * 3},
                  references=REFS, level=0.7).record({"a": "7:00", "b": "7:30"})
    r.plot_handicaps(str(tmp_path / "h.png"))
    r.plot_results(str(tmp_path / "r.png"))
    m = MixedRace(time=1200, references=REFS, lanes={1: ("A", "Senior M", "X"),
                                                     2: ("B", "Junior W", "Y")})
    m.record({1: 5000, 2: 4300})
    m.plot_handicaps(str(tmp_path / "mh.png"))
    m.plot_results(str(tmp_path / "mr.png"))
    assert all((tmp_path / f).exists() for f in ("h.png", "r.png", "mh.png", "mr.png"))


# ── crew race ───────────────────────────────────────────────────────────────
from ergrace import BoatReferences, CrewRace  # noqa: E402

BOATS = BoatReferences(2000, {
    "1x": {"Senior M": "6:40", "Senior W": "7:12"},
    "4x": {"Senior M": "5:45", "Senior W": "6:12.6", "Junior M": "6:02.3"},
})


def test_crew_reference_is_mean_of_seat_powers():
    race = CrewRace(distance=2000, references=BOATS,
                    crews={"mix": ("4x", {"Senior M": 2, "Senior W": 2})})
    vm, vw = BOATS.speed("4x", "Senior M"), BOATS.speed("4x", "Senior W")
    v = ((2 * vm ** 3 + 2 * vw ** 3) / 4) ** (1 / 3)
    assert race.entries["mix"]["ref_speed"] == pytest.approx(v)
    # power mean with exponent 3 lies above the arithmetic mean of speeds
    assert v > (vm + vw) / 2


def test_crew_homogeneous_matches_table_and_uniform_effort():
    race = CrewRace(distance=2000, references=BOATS, crews={
        "1x": ("1x", "Senior W"), "4x": ("4x", ["Senior M", "Junior M", "Senior M", "Senior W"])})
    hc = race.handicaps().set_index("Entry")
    assert hc.loc["1x", "Expected Time (s)"] == pytest.approx(432.0)
    sigma = 0.66
    res = {n: 2000 / (race.entries[n]["ref_speed"] * sigma ** (1 / 3)) for n in race.entries}
    assert np.allclose(race.record(res).results()["Score"], sigma)


def test_crew_seat_count_checked():
    with pytest.raises(ValueError):
        CrewRace(distance=2000, references=BOATS, crews={"x": ("4x", ["Senior M"] * 3)})
    with pytest.raises(KeyError):
        CrewRace(distance=2000, references=BOATS, crews={"x": ("2x", ["Senior M"] * 2)})


def test_default_boat_table_loads():
    race = CrewRace(time="20:00", crews={"a": ("8+", {"Senior M": 4, "Senior W": 4}),
                                         "b": ("1x", "Master W")})
    assert len(race.handicaps()) == 2


# ── fatigue option ──────────────────────────────────────────────────────────
def test_fatigue_off_changes_nothing_and_zero_is_off():
    a = RelayRace(time=1800, teams={"t": TEAM}, references=REFS)
    b = RelayRace(time=1800, teams={"t": TEAM}, references=REFS, fatigue=0)
    assert a.entries["t"]["ref_speed"] == b.entries["t"]["ref_speed"]


def test_fatigue_at_reference_distance_is_neutral():
    race = MixedRace(distance=2000, references=REFS, fatigue=5, lanes={1: "Senior M"})
    assert race.entries["Lane 1"]["ref_speed"] == pytest.approx(V["Senior M"])


def test_fatigue_pauls_law_and_team_size():
    race = MixedRace(distance=8000, references=REFS, fatigue=5, lanes={1: "Senior W"})
    split = 500 / race.entries["Lane 1"]["ref_speed"]
    assert split == pytest.approx(500 / V["Senior W"] + 5 * 2)   # two doublings
    # one rower for 30 min rows longer than each of five -> slower reference
    r = RelayRace(time=1800, references=REFS, fatigue=5,
                  teams={"solo": ["Senior W"], "five": ["Senior W"] * 5})
    assert r.entries["solo"]["ref_speed"] < r.entries["five"]["ref_speed"]
    r0 = RelayRace(time=1800, references=REFS,
                   teams={"solo": ["Senior W"], "five": ["Senior W"] * 5})
    assert r0.entries["solo"]["ref_speed"] == pytest.approx(r0.entries["five"]["ref_speed"])


def test_crew_race_reproduces_former_handicaprace_numbers():
    """Regression: the removed HandicapRace gave these times for Rådasjön runt 2026."""
    race = CrewRace(distance=6000, crews={
        "mix 8+": ("8+", {"Senior M": 4, "Senior W": 4}, 2),
        "M 1x": ("1x", "Senior M", 9),
        "jun 2x": ("2x", ["Junior W", "Junior M"], 1),
        "mix 2x": ("2x", ["Senior M", "Senior W"], 3)})
    hc = race.handicaps().set_index("Entry")
    assert hc.loc["mix 8+", "Expected Time"] == "16:35.5"
    assert hc.loc["M 1x", "Expected Time"] == "20:00.0"
    assert hc.loc["jun 2x", "Expected Time"] == "20:08.6"
    assert hc.loc["mix 2x", "Expected Time"] == "19:11.0"
    assert hc.loc["mix 8+", "No."] == 2
    assert hc.loc["M 1x", "Gap to Prev (s)"] == pytest.approx(8.6, abs=0.05)

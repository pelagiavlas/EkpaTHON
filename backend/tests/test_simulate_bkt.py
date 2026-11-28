"""The presentation simulation runs and is reproducible."""

from scripts.simulate_bkt import run


def test_simulation_is_deterministic_and_complete():
    a, b = run(students=40), run(students=40)
    assert a == b
    assert len(a) == 6 and {r["method"] for r in a} == {"BKT", "Απλοί κανόνες"}


def test_bkt_is_fooled_less_by_lucky_guesses_on_two_choices():
    rows = run(students=200)
    two = {r["method"]: r for r in rows if r["scenario"] == "Ερωτήσεις 2 επιλογών"}
    assert two["BKT"]["early"] < two["Απλοί κανόνες"]["early"]

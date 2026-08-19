from evaluation.evaluate_generation import parse_verdict


def test_parse_verdict_recognizes_yes():
    assert parse_verdict("YES\nBecause the claim is supported.") == "yes"


def test_parse_verdict_recognizes_no():
    assert parse_verdict("NO\nThe answer invents a fact.") == "no"


def test_parse_verdict_is_case_insensitive():
    assert parse_verdict("yes\nlooks fine") == "yes"


def test_parse_verdict_ignores_surrounding_whitespace():
    assert parse_verdict("   YES   \nreason here") == "yes"


def test_parse_verdict_unknown_when_unrecognized():
    assert parse_verdict("Maybe, it's unclear.") == "unknown"


def test_parse_verdict_unknown_when_empty():
    assert parse_verdict("") == "unknown"
    assert parse_verdict("   ") == "unknown"

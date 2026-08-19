from evaluation.evaluate_retrieval import (
    is_hit,
    precision_at_k,
    reciprocal_rank,
)


def test_is_hit_true_when_expected_page_retrieved():
    assert is_hit({1, 2}, [3, 2, 5]) is True


def test_is_hit_false_when_no_overlap():
    assert is_hit({1, 2}, [3, 4, 5]) is False


def test_is_hit_false_when_retrieved_pages_empty():
    assert is_hit({1, 2}, []) is False


def test_precision_at_k_counts_relevant_fraction():
    assert precision_at_k({1, 2}, [1, 3, 2, 4]) == 0.5


def test_precision_at_k_zero_when_no_overlap():
    assert precision_at_k({1}, [2, 3]) == 0.0


def test_precision_at_k_zero_when_retrieved_pages_empty():
    assert precision_at_k({1}, []) == 0.0


def test_reciprocal_rank_uses_first_hit_position():
    assert reciprocal_rank({2}, [3, 2, 5]) == 0.5


def test_reciprocal_rank_full_score_for_top_hit():
    assert reciprocal_rank({1}, [1, 2, 3]) == 1.0


def test_reciprocal_rank_zero_when_no_hit():
    assert reciprocal_rank({9}, [1, 2, 3]) == 0.0

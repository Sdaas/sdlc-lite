from mypackage.textstats import word_count


def test_word_count_counts_words() -> None:
    assert word_count("the quick brown fox") == 4


def test_word_count_empty_text_is_zero() -> None:
    assert word_count("   ") == 0

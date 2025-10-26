from pychub.helper.stream import Stream


# ============================================================================
# __init__ tests
# ============================================================================

def test_stream_init_from_list():
    """Test Stream can be initialized from a list."""
    s = Stream([1, 2, 3])
    assert s.to_list() == [1, 2, 3]


def test_stream_init_from_generator():
    """Test Stream can be initialized from a generator."""
    def gen():
        yield 1
        yield 2
        yield 3
    s = Stream(gen())
    assert s.to_list() == [1, 2, 3]


def test_stream_init_from_range():
    """Test Stream can be initialized from a range."""
    s = Stream(range(5))
    assert s.to_list() == [0, 1, 2, 3, 4]


# ============================================================================
# map tests
# ============================================================================

def test_map_basic():
    """Test map applies function to each element."""
    result = Stream([1, 2, 3]).map(lambda x: x * 2).to_list()
    assert result == [2, 4, 6]


def test_map_chained():
    """Test multiple map operations can be chained."""
    result = Stream([1, 2, 3]).map(lambda x: x * 2).map(lambda x: x + 1).to_list()
    assert result == [3, 5, 7]


def test_map_empty_stream():
    """Test map on empty stream."""
    result = Stream([]).map(lambda x: x * 2).to_list()
    assert result == []


# ============================================================================
# filter tests
# ============================================================================

def test_filter_basic():
    """Test filter keeps only matching elements."""
    result = Stream([1, 2, 3, 4, 5]).filter(lambda x: x % 2 == 0).to_list()
    assert result == [2, 4]


def test_filter_none_match():
    """Test filter when no elements match."""
    result = Stream([1, 3, 5]).filter(lambda x: x % 2 == 0).to_list()
    assert result == []


def test_filter_all_match():
    """Test filter when all elements match."""
    result = Stream([2, 4, 6]).filter(lambda x: x % 2 == 0).to_list()
    assert result == [2, 4, 6]


# ============================================================================
# flat_map tests
# ============================================================================

def test_flat_map_basic():
    """Test flat_map flattens nested iterables."""
    result = Stream([1, 2, 3]).flat_map(lambda x: [x, x * 2]).to_list()
    assert result == [1, 2, 2, 4, 3, 6]


def test_flat_map_with_strings():
    """Test flat_map with strings (iterables)."""
    result = Stream(["ab", "cd"]).flat_map(lambda s: list(s)).to_list()
    assert result == ["a", "b", "c", "d"]


def test_flat_map_empty_results():
    """Test flat_map when function returns empty iterables."""
    result = Stream([1, 2, 3]).flat_map(lambda x: []).to_list()
    assert result == []


# ============================================================================
# distinct tests
# ============================================================================

def test_distinct_removes_duplicates():
    """Test distinct removes duplicate elements."""
    result = Stream([1, 2, 2, 3, 3, 3]).distinct().to_list()
    assert result == [1, 2, 3]


def test_distinct_preserves_order():
    """Test distinct preserves first occurrence order."""
    result = Stream([3, 1, 2, 1, 3]).distinct().to_list()
    assert result == [3, 1, 2]


def test_distinct_empty_stream():
    """Test distinct on empty stream."""
    result = Stream([]).distinct().to_list()
    assert result == []


def test_distinct_no_duplicates():
    """Test distinct when no duplicates exist."""
    result = Stream([1, 2, 3]).distinct().to_list()
    assert result == [1, 2, 3]


# ============================================================================
# peek tests
# ============================================================================

def test_peek_executes_side_effect():
    """Test peek executes function on each element."""
    seen = []
    result = Stream([1, 2, 3]).peek(lambda x: seen.append(x)).to_list()
    assert result == [1, 2, 3]
    assert seen == [1, 2, 3]


def test_peek_returns_stream():
    """Test peek returns a Stream for chaining."""
    result = Stream([1, 2, 3]).peek(lambda x: None).map(lambda x: x * 2).to_list()
    assert result == [2, 4, 6]


# ============================================================================
# sorted tests
# ============================================================================

def test_sorted_ascending():
    """Test sorted sorts in ascending order by default."""
    result = Stream([3, 1, 2]).sorted().to_list()
    assert result == [1, 2, 3]


def test_sorted_descending():
    """Test sorted with reverse=True."""
    result = Stream([3, 1, 2]).sorted(reverse=True).to_list()
    assert result == [3, 2, 1]


def test_sorted_with_key():
    """Test sorted with custom key function."""
    result = Stream(["aaa", "b", "cc"]).sorted(key=len).to_list()
    assert result == ["b", "cc", "aaa"]


def test_sorted_empty_stream():
    """Test sorted on empty stream."""
    result = Stream([]).sorted().to_list()
    assert result == []


# ============================================================================
# limit tests
# ============================================================================

def test_limit_takes_first_n():
    """Test limit takes only first n elements."""
    result = Stream([1, 2, 3, 4, 5]).limit(3).to_list()
    assert result == [1, 2, 3]


def test_limit_more_than_available():
    """Test limit with n greater than stream size."""
    result = Stream([1, 2, 3]).limit(10).to_list()
    assert result == [1, 2, 3]


def test_limit_zero():
    """Test limit(0) returns empty stream."""
    result = Stream([1, 2, 3]).limit(0).to_list()
    assert result == []


# ============================================================================
# skip tests
# ============================================================================

def test_skip_skips_first_n():
    """Test skip skips first n elements."""
    result = Stream([1, 2, 3, 4, 5]).skip(2).to_list()
    assert result == [3, 4, 5]


def test_skip_more_than_available():
    """Test skip with n greater than stream size."""
    result = Stream([1, 2, 3]).skip(10).to_list()
    assert result == []


def test_skip_zero():
    """Test skip(0) returns full stream."""
    result = Stream([1, 2, 3]).skip(0).to_list()
    assert result == [1, 2, 3]


# ============================================================================
# to_list tests
# ============================================================================

def test_to_list_basic():
    """Test to_list converts stream to list."""
    result = Stream([1, 2, 3]).to_list()
    assert result == [1, 2, 3]
    assert isinstance(result, list)


# ============================================================================
# to_set tests
# ============================================================================

def test_to_set_basic():
    """Test to_set converts stream to set."""
    result = Stream([1, 2, 2, 3]).to_set()
    assert result == {1, 2, 3}
    assert isinstance(result, set)


# ============================================================================
# count tests
# ============================================================================

def test_count_basic():
    """Test count returns number of elements."""
    result = Stream([1, 2, 3, 4, 5]).count()
    assert result == 5


def test_count_empty():
    """Test count on empty stream."""
    result = Stream([]).count()
    assert result == 0


def test_count_after_filter():
    """Test count after filter."""
    result = Stream([1, 2, 3, 4, 5]).filter(lambda x: x % 2 == 0).count()
    assert result == 2


# ============================================================================
# find_first tests
# ============================================================================

def test_find_first_returns_first_element():
    """Test find_first returns first element."""
    result = Stream([1, 2, 3]).find_first()
    assert result == 1


def test_find_first_empty_stream():
    """Test find_first on empty stream returns None."""
    result = Stream([]).find_first()
    assert result is None


def test_find_first_after_filter():
    """Test find_first after filter."""
    result = Stream([1, 2, 3, 4]).filter(lambda x: x > 2).find_first()
    assert result == 3


# ============================================================================
# any_match tests
# ============================================================================

def test_any_match_true():
    """Test any_match returns True when at least one matches."""
    result = Stream([1, 2, 3, 4]).any_match(lambda x: x > 3)
    assert result is True


def test_any_match_false():
    """Test any_match returns False when none match."""
    result = Stream([1, 2, 3]).any_match(lambda x: x > 10)
    assert result is False


def test_any_match_empty():
    """Test any_match on empty stream."""
    result = Stream([]).any_match(lambda x: True)
    assert result is False


# ============================================================================
# all_match tests
# ============================================================================

def test_all_match_true():
    """Test all_match returns True when all match."""
    result = Stream([2, 4, 6]).all_match(lambda x: x % 2 == 0)
    assert result is True


def test_all_match_false():
    """Test all_match returns False when at least one doesn't match."""
    result = Stream([2, 3, 4]).all_match(lambda x: x % 2 == 0)
    assert result is False


def test_all_match_empty():
    """Test all_match on empty stream."""
    result = Stream([]).all_match(lambda x: False)
    assert result is True  # All elements in empty stream vacuously satisfy


# ============================================================================
# none_match tests
# ============================================================================

def test_none_match_true():
    """Test none_match returns True when none match."""
    result = Stream([1, 3, 5]).none_match(lambda x: x % 2 == 0)
    assert result is True


def test_none_match_false():
    """Test none_match returns False when at least one matches."""
    result = Stream([1, 2, 3]).none_match(lambda x: x % 2 == 0)
    assert result is False


def test_none_match_empty():
    """Test none_match on empty stream."""
    result = Stream([]).none_match(lambda x: True)
    assert result is True


# ============================================================================
# reduce tests
# ============================================================================

def test_reduce_with_initializer():
    """Test reduce with initializer."""
    result = Stream([1, 2, 3, 4]).reduce(lambda a, b: a + b, 0)
    assert result == 10


def test_reduce_without_initializer():
    """Test reduce without initializer."""
    result = Stream([1, 2, 3, 4]).reduce(lambda a, b: a + b)
    assert result == 10


def test_reduce_single_element():
    """Test reduce on single element stream."""
    result = Stream([5]).reduce(lambda a, b: a + b)
    assert result == 5


def test_reduce_multiplication():
    """Test reduce with multiplication."""
    result = Stream([1, 2, 3, 4]).reduce(lambda a, b: a * b, 1)
    assert result == 24


# ============================================================================
# for_each tests
# ============================================================================

def test_for_each_executes_on_all():
    """Test for_each executes function on all elements."""
    results = []
    Stream([1, 2, 3]).for_each(lambda x: results.append(x * 2))
    assert results == [2, 4, 6]


def test_for_each_returns_none():
    """Test for_each returns None."""
    result = Stream([1, 2, 3]).for_each(lambda x: None)
    assert result is None


# ============================================================================
# to_dict tests
# ============================================================================

def test_to_dict_basic():
    """Test to_dict with key function only."""
    result = Stream([1, 2, 3]).to_dict(lambda x: x)
    assert result == {1: 1, 2: 2, 3: 3}


def test_to_dict_with_value_fn():
    """Test to_dict with both key and value functions."""
    result = Stream([1, 2, 3]).to_dict(lambda x: x, lambda x: x * 2)
    assert result == {1: 2, 2: 4, 3: 6}


def test_to_dict_from_tuples():
    """Test to_dict from list of tuples."""
    result = Stream([("a", 1), ("b", 2)]).to_dict(lambda t: t[0], lambda t: t[1])
    assert result == {"a": 1, "b": 2}


# ============================================================================
# group_by tests
# ============================================================================

def test_group_by_basic():
    """Test group_by groups elements by key."""
    result = Stream([1, 2, 3, 4, 5]).group_by(lambda x: x % 2)
    assert result == {0: [2, 4], 1: [1, 3, 5]}


def test_group_by_strings():
    """Test group_by with string length."""
    result = Stream(["a", "bb", "c", "dd"]).group_by(len)
    assert result == {1: ["a", "c"], 2: ["bb", "dd"]}


def test_group_by_empty():
    """Test group_by on empty stream."""
    result = Stream([]).group_by(lambda x: x)
    assert result == {}


# ============================================================================
# partition_by tests
# ============================================================================

def test_partition_by_basic():
    """Test partition_by splits into True/False groups."""
    result = Stream([1, 2, 3, 4, 5]).partition_by(lambda x: x % 2 == 0)
    assert result == {True: [2, 4], False: [1, 3, 5]}


def test_partition_by_all_true():
    """Test partition_by when all match."""
    result = Stream([2, 4, 6]).partition_by(lambda x: x % 2 == 0)
    assert result == {True: [2, 4, 6], False: []}


def test_partition_by_all_false():
    """Test partition_by when none match."""
    result = Stream([1, 3, 5]).partition_by(lambda x: x % 2 == 0)
    assert result == {True: [], False: [1, 3, 5]}


# ============================================================================
# Chaining tests
# ============================================================================

def test_complex_chain():
    """Test complex chain of operations."""
    result = (Stream([1, 2, 3, 4, 5, 6])
              .filter(lambda x: x % 2 == 0)
              .map(lambda x: x * 2)
              .distinct()
              .sorted()
              .to_list())
    assert result == [4, 8, 12]


def test_chain_with_limit_and_skip():
    """Test chaining limit and skip."""
    result = Stream(range(10)).skip(2).limit(3).to_list()
    assert result == [2, 3, 4]


def test_chain_ending_with_terminal():
    """Test chain ending with various terminal operations."""
    assert Stream([1, 2, 3]).map(lambda x: x * 2).count() == 3
    assert Stream([1, 2, 3]).filter(lambda x: x > 1).find_first() == 2
    assert Stream([1, 2, 3]).any_match(lambda x: x == 2) is True
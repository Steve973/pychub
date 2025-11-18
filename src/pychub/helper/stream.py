from functools import reduce as _reduce
from itertools import islice, tee, groupby
from typing import Any


class Stream:
    def __init__(self, iterable):
        self._it = iter(iterable)

    def map(self, fn):
        return Stream(map(fn, self._it))

    def filter(self, pred):
        return Stream(filter(pred, self._it))

    def flat_map(self, fn):
        # fn returns iterable for each item
        return Stream(x for item in self._it for x in fn(item))

    def distinct(self):
        seen = set()

        def mark_seen(x: Any) -> bool:
            seen.add(x)
            return True

        return Stream(x for x in self._it if x not in seen and mark_seen(x))

    def peek(self, fn):
        def generator():
            for x in self._it:
                fn(x)
                yield x

        return Stream(generator())

    def sorted(self, key=None, reverse=False):
        return Stream(sorted(self._it, key=key, reverse=reverse))

    def limit(self, n):
        return Stream(islice(self._it, n))

    def skip(self, n):
        # Consume n elements, then yield rest
        def generator():
            it = self._it
            for _ in range(n):
                next(it, None)
            yield from it

        return Stream(generator())

    # Terminal ops
    def to_list(self):
        return list(self._it)

    def to_set(self):
        return set(self._it)

    def count(self):
        return sum(1 for _ in self._it)

    def find_first(self):
        try:
            return next(self._it)
        except StopIteration:
            return None

    def any_match(self, pred):
        return any(pred(x) for x in self._it)

    def all_match(self, pred):
        return all(pred(x) for x in self._it)

    def none_match(self, pred):
        return not any(pred(x) for x in self._it)

    def reduce(self, fn, initializer=None):
        if initializer is not None:
            return _reduce(fn, self._it, initializer)
        return _reduce(fn, self._it)

    def for_each(self, fn):
        for x in self._it:
            fn(x)
        # Java's forEach returns void; in Python, return None for clarity

    # Extra pythonic/fat-and-sassy features:
    def to_dict(self, key_fn, value_fn=lambda x: x):
        return {key_fn(x): value_fn(x) for x in self._it}

    def group_by(self, key_fn):
        sorted_it = sorted(self._it, key=key_fn)
        return {k: list(g) for k, g in groupby(sorted_it, key_fn)}

    def partition_by(self, pred):
        t1, t2 = tee(self._it)
        return {
            True: [x for x in t1 if pred(x)],
            False: [x for x in t2 if not pred(x)]
        }

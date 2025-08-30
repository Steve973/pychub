from __future__ import annotations

import attr

@attr.s
class Greeter:
    name = attr.ib(type=str)

def main(**argv: str):
    thing = Greeter(name="test-run")
    args = ""
    if argv:
        args = ", ".join(argv)
        args = f"Includes arguments: {args}"
    print(f"Hello from {thing.name}!", args)

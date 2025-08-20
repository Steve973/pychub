import attr

@attr.s
class Greeter:
    name = attr.ib(type=str)

def main():
    thing = Greeter(name="test-run")
    print(f"Hello from {thing.name}!")

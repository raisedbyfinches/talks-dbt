#!/usr/bin/env python3
from typing import TypeVar, Callable, Protocol, List, Optional, Iterator, Generator, Any

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')

class Functor(Protocol[T]):
    def map(self, func: Callable[[T], U]) -> 'Functor[U]':
        ...

def lift(func: Callable[[T], U]) -> Callable[[Functor[T]], Functor[U]]:
    def lifted(functor: Functor[T]) -> Functor[U]:
        return functor.map(func)
    return lifted

def compose_functors(f1: Callable[[T], U], f2: Callable[[U], V]) -> Callable[[Functor[T]], Functor[V]]:
    return lambda x: x.map(f1).map(f2)

# List Functor
class ListFunctor(List[T]):
    def map(self, func: Callable[[T], U]) -> 'ListFunctor[U]':
        return ListFunctor(func(x) for x in self)

# Optional Functor as a wrapper
class OptionalFunctor:
    def __init__(self, value: Optional[T]):
        self._value = value

    def map(self, func: Callable[[T], U]) -> 'OptionalFunctor[U]':
        return OptionalFunctor(func(self._value) if self._value is not None else None)

    def __repr__(self):
        return f"OptionalFunctor({self._value})"

# Generator Functor
class GeneratorFunctor:
    def __init__(self, gen: Iterator[T]):
        self.gen = gen

    def map(self, func: Callable[[T], U]) -> 'GeneratorFunctor[U]':
        return GeneratorFunctor(func(x) for x in self.gen)

# Demonstration
def main():
    # List functor
    numbers = ListFunctor([1, 2, 3, 4])
    squared = numbers.map(lambda x: x ** 2)
    print("Squared numbers:", squared)

    # Optional functor
    maybe_value: Optional[int] = 5
    optional_func = OptionalFunctor(maybe_value)
    doubled = optional_func.map(lambda x: x * 2)
    print("Doubled value:", doubled)

    # Optional functor with None
    none_value: Optional[int] = None
    none_func = OptionalFunctor(none_value)
    none_doubled = none_func.map(lambda x: x * 2)
    print("None doubled:", none_doubled)

    # Lifting a function
    def add_five(x: int) -> int:
        return x + 5

    lifted_add_five = lift(add_five)
    print("Lifted add_five on list:", lifted_add_five(numbers))

    # Function composition on functors
    composed = compose_functors(
        lambda x: x * 2,  # first transform
        lambda x: x + 3   # then transform
    )
    print("Composed transformation:", composed(numbers))

if __name__ == "__main__":
    main()

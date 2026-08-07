"""
Calculator module - Core calculator logic and CLI interface.
"""

import math
import sys
from typing import Union, List, Optional

import click


class CalculatorError(Exception):
    """Base exception for calculator errors."""
    pass


class DivisionByZeroError(CalculatorError):
    """Raised when division by zero is attempted."""
    pass


class InvalidInputError(CalculatorError):
    """Raised when input is invalid."""
    pass


class Calculator:
    """
    A calculator class supporting basic and advanced arithmetic operations.
    
    Supported operations:
    - add: Addition
    - sub: Subtraction
    - mul: Multiplication
    - div: Division
    - pow: Power (exponentiation)
    - mod: Modulo
    - sqrt: Square root
    - fact: Factorial
    """
    
    def __init__(self):
        self.history: List[str] = []
    
    def _validate_number(self, value: Union[str, float, int]) -> float:
        """Validate and convert input to float."""
        try:
            return float(value)
        except (ValueError, TypeError) as e:
            raise InvalidInputError(f"Invalid number: {value}") from e
    
    def add(self, a: Union[str, float, int], b: Union[str, float, int]) -> float:
        """Add two numbers."""
        a = self._validate_number(a)
        b = self._validate_number(b)
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
    
    def subtract(self, a: Union[str, float, int], b: Union[str, float, int]) -> float:
        """Subtract b from a."""
        a = self._validate_number(a)
        b = self._validate_number(b)
        result = a - b
        self.history.append(f"sub({a}, {b}) = {result}")
        return result
    
    def multiply(self, a: Union[str, float, int], b: Union[str, float, int]) -> float:
        """Multiply two numbers."""
        a = self._validate_number(a)
        b = self._validate_number(b)
        result = a * b
        self.history.append(f"mul({a}, {b}) = {result}")
        return result
    
    def divide(self, a: Union[str, float, int], b: Union[str, float, int]) -> float:
        """Divide a by b."""
        a = self._validate_number(a)
        b = self._validate_number(b)
        if b == 0:
            raise DivisionByZeroError("Cannot divide by zero")
        result = a / b
        self.history.append(f"div({a}, {b}) = {result}")
        return result
    
    def power(self, base: Union[str, float, int], exp: Union[str, float, int]) -> float:
        """Raise base to the power of exp."""
        base = self._validate_number(base)
        exp = self._validate_number(exp)
        result = math.pow(base, exp)
        self.history.append(f"pow({base}, {exp}) = {result}")
        return result
    
    def modulo(self, a: Union[str, float, int], b: Union[str, float, int]) -> float:
        """Return the remainder of a divided by b."""
        a = self._validate_number(a)
        b = self._validate_number(b)
        if b == 0:
            raise DivisionByZeroError("Cannot compute modulo with zero")
        result = a % b
        self.history.append(f"mod({a}, {b}) = {result}")
        return result
    
    def square_root(self, n: Union[str, float, int]) -> float:
        """Return the square root of n."""
        n = self._validate_number(n)
        if n < 0:
            raise InvalidInputError("Cannot compute square root of negative number")
        result = math.sqrt(n)
        self.history.append(f"sqrt({n}) = {result}")
        return result
    
    def factorial(self, n: Union[str, float, int]) -> float:
        """Return the factorial of n (n must be a non-negative integer)."""
        n = self._validate_number(n)
        if not n.is_integer():
            raise InvalidInputError("Factorial is only defined for integers")
        n = int(n)
        if n < 0:
            raise InvalidInputError("Factorial is not defined for negative numbers")
        result = math.factorial(n)
        self.history.append(f"fact({n}) = {result}")
        return result
    
    def get_history(self) -> List[str]:
        """Return the calculation history."""
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Clear the calculation history."""
        self.history.clear()


def calculate(operation: str, *args: Union[str, float, int], **kwargs) -> float:
    """
    Calculate a result using the specified operation.
    
    Args:
        operation: The operation to perform (add, sub, mul, div, pow, mod, sqrt, fact)
        *args: Arguments for the operation
        **kwargs: Additional keyword arguments
    
    Returns:
        The calculated result
    
    Raises:
        CalculatorError: If the operation is invalid or inputs are invalid
    """
    calc = Calculator()
    
    operations = {
        'add': calc.add,
        'sub': calc.subtract,
        'mul': calc.multiply,
        'div': calc.divide,
        'pow': calc.power,
        'mod': calc.modulo,
        'sqrt': calc.square_root,
        'fact': calc.factorial,
    }
    
    if operation not in operations:
        raise InvalidInputError(f"Unknown operation: {operation}. "
                               f"Supported operations: {', '.join(operations.keys())}")
    
    return operations[operation](*args, **kwargs)


@click.group(invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Show version information')
@click.option('--help', '-h', is_flag=True, help='Show help message')
@click.pass_context
def cli(ctx: click.Context, version: bool, help: bool) -> None:
    """
    CLI Calculator - A powerful command-line calculator.
    
    Supported operations:
      add       Addition: add 5 3
      sub       Subtraction: sub 10 4
      mul       Multiplication: mul 6 7
      div       Division: div 20 4
      pow       Power: pow 2 3 (2^3)
      mod       Modulo: mod 17 5
      sqrt      Square root: sqrt 16
      fact      Factorial: fact 5
    
    Examples:
      calculator add 5 3
      calculator sub 10 4
      calculator mul 6 7
      calculator div 20 4
      calculator pow 2 3
      calculator mod 17 5
      calculator sqrt 16
      calculator fact 5
      calculator --help
    """
    if version:
        click.echo(f"CLI Calculator v1.0.0")
        ctx.exit(0)
    
    if help or ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@cli.command('add')
@click.argument('a', type=click.FLOAT)
@click.argument('b', type=click.FLOAT)
def add_cmd(a: float, b: float) -> None:
    """Add two numbers."""
    result = calculate('add', a, b)
    click.echo(f"{a} + {b} = {result}")


@cli.command('sub')
@click.argument('a', type=click.FLOAT)
@click.argument('b', type=click.FLOAT)
def sub_cmd(a: float, b: float) -> None:
    """Subtract b from a."""
    result = calculate('sub', a, b)
    click.echo(f"{a} - {b} = {result}")


@cli.command('mul')
@click.argument('a', type=click.FLOAT)
@click.argument('b', type=click.FLOAT)
def mul_cmd(a: float, b: float) -> None:
    """Multiply two numbers."""
    result = calculate('mul', a, b)
    click.echo(f"{a} * {b} = {result}")


@cli.command('div')
@click.argument('a', type=click.FLOAT)
@click.argument('b', type=click.FLOAT)
def div_cmd(a: float, b: float) -> None:
    """Divide a by b."""
    result = calculate('div', a, b)
    click.echo(f"{a} / {b} = {result}")


@cli.command('pow')
@click.argument('base', type=click.FLOAT)
@click.argument('exp', type=click.FLOAT)
def pow_cmd(base: float, exp: float) -> None:
    """Raise base to the power of exp."""
    result = calculate('pow', base, exp)
    click.echo(f"{base} ^ {exp} = {result}")


@cli.command('mod')
@click.argument('a', type=click.FLOAT)
@click.argument('b', type=click.FLOAT)
def mod_cmd(a: float, b: float) -> None:
    """Return the remainder of a divided by b."""
    result = calculate('mod', a, b)
    click.echo(f"{a} % {b} = {result}")


@cli.command('sqrt')
@click.argument('n', type=click.FLOAT)
def sqrt_cmd(n: float) -> None:
    """Return the square root of n."""
    result = calculate('sqrt', n)
    click.echo(f"sqrt({n}) = {result}")


@cli.command('fact')
@click.argument('n', type=click.INT)
def fact_cmd(n: int) -> None:
    """Return the factorial of n."""
    result = calculate('fact', n)
    click.echo(f"fact({n}) = {result}")


def main() -> int:
    """Main entry point for the CLI calculator."""
    return cli()


if __name__ == '__main__':
    sys.exit(main())

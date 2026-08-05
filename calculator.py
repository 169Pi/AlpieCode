"""
Calculator module providing arithmetic operations.
"""

import math
from typing import Union


class CalculatorError(Exception):
    """Base exception for calculator errors."""
    pass


class DivisionByZeroError(CalculatorError):
    """Raised when dividing by zero."""
    pass


class InvalidInputError(CalculatorError):
    """Raised when input is invalid."""
    pass


class Calculator:
    """A simple calculator class with basic arithmetic operations."""

    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Sum of a and b
            
        Raises:
            CalculatorError: If inputs are not numbers
        """
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidInputError("Both arguments must be numbers")
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtract b from a.
        
        Args:
            a: First number (minuend)
            b: Second number (subtrahend)
            
        Returns:
            Difference of a and b
            
        Raises:
            CalculatorError: If inputs are not numbers
        """
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidInputError("Both arguments must be numbers")
        return a - b

    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Product of a and b
            
        Raises:
            CalculatorError: If inputs are not numbers
        """
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidInputError("Both arguments must be numbers")
        return a * b

    def divide(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Divide a by b.
        
        Args:
            a: Dividend
            b: Divisor
            
        Returns:
            Quotient of a divided by b
            
        Raises:
            DivisionByZeroError: If b is zero
            CalculatorError: If inputs are not numbers
        """
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidInputError("Both arguments must be numbers")
        if b == 0:
            raise DivisionByZeroError("Cannot divide by zero")
        return a / b

    def power(self, base: Union[int, float], exponent: Union[int, float]) -> Union[int, float]:
        """Raise base to the power of exponent.
        
        Args:
            base: The base number
            exponent: The exponent
            
        Returns:
            base raised to the power of exponent
            
        Raises:
            CalculatorError: If inputs are not numbers
        """
        if not isinstance(base, (int, float)) or not isinstance(exponent, (int, float)):
            raise InvalidInputError("Both arguments must be numbers")
        return base ** exponent

    def modulo(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Calculate the modulo (remainder) of a divided by b.
        
        Args:
            a: Dividend
            b: Divisor
            
        Returns:
            Remainder of a divided by b
            
        Raises:
            DivisionByZeroError: If b is zero
            CalculatorError: If inputs are not numbers
        """
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidInputError("Both arguments must be numbers")
        if b == 0:
            raise DivisionByZeroError("Cannot calculate modulo with zero divisor")
        return a % b

    def sqrt(self, x: Union[int, float]) -> float:
        """Calculate the square root of x.
        
        Args:
            x: The number to find the square root of
            
        Returns:
            Square root of x
            
        Raises:
            CalculatorError: If x is negative or not a number
        """
        if not isinstance(x, (int, float)):
            raise InvalidInputError("Argument must be a number")
        if x < 0:
            raise InvalidInputError("Cannot calculate square root of negative number")
        return math.sqrt(x)

    def factorial(self, n: int) -> int:
        """Calculate the factorial of n.
        
        Args:
            n: Non-negative integer
            
        Returns:
            Factorial of n
            
        Raises:
            CalculatorError: If n is negative or not an integer
        """
        if not isinstance(n, int):
            raise InvalidInputError("Argument must be an integer")
        if n < 0:
            raise InvalidInputError("Factorial is not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    def sin(self, x: Union[int, float]) -> float:
        """Calculate the sine of x (x is in radians).
        
        Args:
            x: Angle in radians
            
        Returns:
            Sine of x
            
        Raises:
            CalculatorError: If x is not a number
        """
        if not isinstance(x, (int, float)):
            raise InvalidInputError("Argument must be a number")
        return math.sin(x)

    def cos(self, x: Union[int, float]) -> float:
        """Calculate the cosine of x (x is in radians).
        
        Args:
            x: Angle in radians
            
        Returns:
            Cosine of x
            
        Raises:
            CalculatorError: If x is not a number
        """
        if not isinstance(x, (int, float)):
            raise InvalidInputError("Argument must be a number")
        return math.cos(x)

    def tan(self, x: Union[int, float]) -> float:
        """Calculate the tangent of x (x is in radians).
        
        Args:
            x: Angle in radians
            
        Returns:
            Tangent of x
            
        Raises:
            CalculatorError: If x is not a number
        """
        if not isinstance(x, (int, float)):
            raise InvalidInputError("Argument must be a number")
        return math.tan(x)

    def log(self, x: Union[int, float], base: Union[int, float] = 10) -> float:
        """Calculate the logarithm of x with the given base.
        
        Args:
            x: The number to find the logarithm of
            base: The base of the logarithm (default: 10)
            
        Returns:
            Logarithm of x with the given base
            
        Raises:
            CalculatorError: If x is not positive or not a number
        """
        if not isinstance(x, (int, float)) or not isinstance(base, (int, float)):
            raise InvalidInputError("Arguments must be numbers")
        if x <= 0:
            raise InvalidInputError("Logarithm is not defined for non-positive numbers")
        if base <= 0 or base == 1:
            raise InvalidInputError("Base must be positive and not equal to 1")
        return math.log(x, base)

    def abs(self, x: Union[int, float]) -> Union[int, float]:
        """Calculate the absolute value of x.
        
        Args:
            x: The number
            
        Returns:
            Absolute value of x
            
        Raises:
            CalculatorError: If x is not a number
        """
        if not isinstance(x, (int, float)):
            raise InvalidInputError("Argument must be a number")
        return abs(x)
"""
Calculator module providing basic arithmetic operations.
"""

from typing import Union


class CalculatorError(Exception):
    """Base exception for calculator errors."""
    pass


class DivisionByZeroError(CalculatorError):
    """Raised when division by zero is attempted."""
    pass


class InvalidOperationError(CalculatorError):
    """Raised when an invalid operation is attempted."""
    pass


class Calculator:
    """
    A simple calculator supporting basic arithmetic operations.
    
    Supported operations:
    - add(a, b): Addition
    - subtract(a, b): Subtraction
    - multiply(a, b): Multiplication
    - divide(a, b): Division
    - power(a, b): Exponentiation
    - modulo(a, b): Modulo operation
    """
    
    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Add two numbers."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidOperationError("Both operands must be numbers")
        return a + b
    
    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtract b from a."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidOperationError("Both operands must be numbers")
        return a - b
    
    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiply two numbers."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidOperationError("Both operands must be numbers")
        return a * b
    
    def divide(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Divide a by b."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidOperationError("Both operands must be numbers")
        if b == 0:
            raise DivisionByZeroError("Cannot divide by zero")
        return a / b
    
    def power(self, base: Union[int, float], exponent: Union[int, float]) -> Union[int, float]:
        """Raise base to the power of exponent."""
        if not isinstance(base, (int, float)) or not isinstance(exponent, (int, float)):
            raise InvalidOperationError("Both operands must be numbers")
        return base ** exponent
    
    def modulo(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Return the remainder of a divided by b."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise InvalidOperationError("Both operands must be numbers")
        if b == 0:
            raise DivisionByZeroError("Cannot compute modulo with zero")
        return a % b
    
    def evaluate(self, expression: str) -> Union[int, float]:
        """
        Evaluate a simple arithmetic expression.
        
        Supported operators: +, -, *, /, **, %
        Example: evaluate("2 + 3 * 4") returns 14
        
        Args:
            expression: A string containing a valid arithmetic expression
            
        Returns:
            The result of the evaluation
            
        Raises:
            CalculatorError: If the expression is invalid
        """
        try:
            # Replace visual operators with Python operators
            expression = expression.replace('×', '*').replace('÷', '/')
            
            # Use eval with restricted namespace for safety
            allowed_names = {
                '__builtins__': {},
                'abs': abs,
                'round': round,
                'int': int,
                'float': float,
                'str': str,
            }
            result = eval(expression, {"__name__": "__main__"}, allowed_names)
            
            # Verify the result is a number
            if not isinstance(result, (int, float)):
                raise InvalidOperationError(f"Expression evaluated to non-numeric result: {result}")
            
            return result
        except ZeroDivisionError:
            raise DivisionByZeroError("Cannot divide by zero")
        except SyntaxError:
            raise InvalidOperationError("Invalid expression syntax")
        except Exception as e:
            raise InvalidOperationError(f"Error evaluating expression: {e}")
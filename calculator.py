#!/usr/bin/env python3
"""
A simple Python CLI calculator with arithmetic operations.

Usage:
    python calculator.py <expression>
    
Examples:
    python calculator.py "2 + 3"
    python calculator.py "10 * 5 - 3"
    python calculator.py "100 / 4"
"""

import argparse
import sys
from typing import Union


class CalculatorError(Exception):
    """Custom exception for calculator errors."""
    pass


class Calculator:
    """A simple calculator supporting basic arithmetic operations."""
    
    def __init__(self):
        """Initialize the calculator."""
        self.history: list[str] = []
    
    def _parse_number(self, value: str) -> float:
        """
        Parse a string value into a float.
        
        Args:
            value: String representation of a number.
            
        Returns:
            The parsed float value.
            
        Raises:
            CalculatorError: If the value cannot be parsed as a number.
        """
        try:
            return float(value)
        except ValueError:
            raise CalculatorError(f"Invalid number: '{value}'")
    
    def add(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        Add two numbers.
        
        Args:
            a: First operand.
            b: Second operand.
            
        Returns:
            The sum of a and b.
        """
        return a + b
    
    def subtract(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        Subtract b from a.
        
        Args:
            a: First operand (minuend).
            b: Second operand (subtrahend).
            
        Returns:
            The difference of a and b.
        """
        return a - b
    
    def multiply(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        Multiply two numbers.
        
        Args:
            a: First operand.
            b: Second operand.
            
        Returns:
            The product of a and b.
        """
        return a * b
    
    def divide(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        Divide a by b.
        
        Args:
            a: Dividend.
            b: Divisor.
            
        Returns:
            The quotient of a divided by b.
            
        Raises:
            CalculatorError: If b is zero (division by zero).
        """
        if b == 0:
            raise CalculatorError("Division by zero is not allowed")
        return a / b
    
    def evaluate(self, expression: str) -> float:
        """
        Evaluate a mathematical expression.
        
        Supports: +, -, *, / operators with standard precedence.
        Supports parentheses for grouping.
        
        Args:
            expression: A mathematical expression string.
            
        Returns:
            The result of evaluating the expression.
            
        Raises:
            CalculatorError: If the expression is invalid or contains
                           unsupported characters.
        """
        # Validate expression contains only allowed characters
        allowed_chars = set("0123456789+-*/(). ")
        for char in expression:
            if char not in allowed_chars:
                raise CalculatorError(f"Invalid character in expression: '{char}'")
        
        # Handle empty expression
        if not expression.strip():
            raise CalculatorError("Empty expression")
        
        # Use eval with restricted namespace for safety
        # This is safe because we've already validated the expression
        result = eval(expression, {"__builtins__": {}}, {})
        
        # Store in history
        self.history.append(f"{expression} = {result}")
        
        return result
    
    def get_history(self) -> list[str]:
        """
        Get the calculation history.
        
        Returns:
            List of calculation strings in format "expression = result".
        """
        return self.history.copy()


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="A simple Python CLI calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "2 + 3"
  %(prog)s "10 * 5 - 3"
  %(prog)s "100 / 4"
  %(prog)s "((2 + 3) * 4) - 1"
        """
    )
    
    parser.add_argument(
        "expression",
        type=str,
        nargs="?",
        default="",
        help="Mathematical expression to evaluate"
    )
    
    parser.add_argument(
        "-H", "--history",
        action="store_true",
        help="Show calculation history"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the CLI calculator.
    
    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = parse_arguments()
    
    calculator = Calculator()
    
    if args.history:
        print("Calculation History:")
        print("-" * 40)
        if calculator.history:
            for entry in calculator.history:
                print(entry)
        else:
            print("No calculations performed yet.")
        return 0
    
    if not args.expression:
        print("Error: No expression provided")
        print("Usage: python calculator.py <expression>")
        return 1
    
    try:
        result = calculator.evaluate(args.expression)
        
        # Format output - avoid floating point representation issues
        if result == int(result):
            print(f"Result: {int(result)}")
        else:
            print(f"Result: {result}")
        
        return 0
        
    except CalculatorError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

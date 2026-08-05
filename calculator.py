"""
Python CLI Calculator Module

Provides arithmetic operations and a command-line interface for calculations.
"""

import re
from typing import Union


def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """Add two numbers."""
    return a + b


def subtract(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """Subtract b from a."""
    return a - b


def multiply(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """Multiply two numbers."""
    return a * b


def divide(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """Divide a by b. Raises ValueError if b is zero."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


def calculate(expression: str) -> Union[int, float]:
    """
    Calculate the result of a mathematical expression.
    
    Supports basic arithmetic operations: +, -, *, /
    Example: calculate("2 + 3 * 4") returns 14
    
    Args:
        expression: A string containing a mathematical expression
        
    Returns:
        The result of the calculation
        
    Raises:
        ValueError: If the expression is invalid or division by zero occurs
        TypeError: If the expression contains non-numeric values
    """
    # Validate the expression contains only valid characters
    pattern = r'^[0-9+\-*/\s().]+$'
    if not re.match(pattern, expression):
        raise ValueError(f"Invalid expression: '{expression}'")
    
    # Check for empty expression
    if not expression.strip():
        raise ValueError("Empty expression")
    
    # Evaluate the expression safely
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return result
    except ZeroDivisionError:
        raise ValueError("Division by zero is not allowed.")
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")


def main():
    """Main entry point for the CLI calculator."""
    print("Python CLI Calculator")
    print("Type 'quit' or 'exit' to exit")
    print("Type 'help' for available commands")
    print()
    
    while True:
        try:
            user_input = input(">>> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ('quit', 'exit'):
                print("Goodbye!")
                break
            
            if user_input.lower() == 'help':
                print("Available commands:")
                print("  +, -, *, /  - Arithmetic operations")
                print("  Example: 2 + 3 * 4")
                print("  Type 'quit' to exit, 'help' for this message")
                continue
            
            try:
                result = calculate(user_input)
                # Format the output - remove unnecessary decimal places
                if isinstance(result, float):
                    if result == int(result):
                        print(f"Result: {int(result)}")
                    else:
                        # Remove trailing zeros
                        formatted = f"{result:.10f}".rstrip('0').rstrip('.')
                        print(f"Result: {formatted}")
                else:
                    print(f"Result: {result}")
            except ValueError as e:
                print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()

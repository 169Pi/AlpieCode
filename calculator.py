"""
Interactive Calculator Module
Provides basic arithmetic operations with error handling.
"""


def add(a, b):
    """Add two numbers."""
    return a + b


def subtract(a, b):
    """Subtract b from a."""
    return a - b


def multiply(a, b):
    """Multiply two numbers."""
    return a * b


def divide(a, b):
    """Divide a by b. Raises ValueError if b is zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base, exponent):
    """Raise base to the power of exponent."""
    return base ** exponent


def calculate(expression):
    """
    Evaluate a mathematical expression string.
    Supports: +, -, *, /, **, parentheses
    """
    import re
    
    # Replace ** with a temporary placeholder for safe evaluation
    temp = expression.replace('**', '\x00POWER\x00')
    
    # Check for invalid characters (allow digits, spaces, +, -, *, /, (, ), ., and ** placeholder)
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.\x00]+$', temp):
        raise ValueError("Invalid characters in expression")
    
    # Replace placeholder back
    temp = temp.replace('\x00POWER\x00', '**')
    
    # Safe evaluation using eval with restricted globals
    result = eval(temp, {"__builtins__": {}}, {})
    return result


if __name__ == "__main__":
    print("=" * 50)
    print("Welcome to the Interactive Calculator")
    print("=" * 50)
    print()
    print("Available operations:")
    print("  add(a, b)       - Addition")
    print("  subtract(a, b)  - Subtraction")
    print("  multiply(a, b)  - Multiplication")
    print("  divide(a, b)    - Division")
    print("  power(base, e)  - Exponentiation")
    print("  calculate(expr) - Evaluate expression string")
    print()
    print("Example: add(5, 3) = 8")
    print()
    
    while True:
        try:
            choice = input("Enter operation (or 'quit' to exit): ").strip()
            
            if choice.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if choice.lower() == 'add':
                a = float(input("Enter first number: "))
                b = float(input("Enter second number: "))
                print(f"Result: {add(a, b)}")
            
            elif choice.lower() == 'subtract':
                a = float(input("Enter first number: "))
                b = float(input("Enter second number: "))
                print(f"Result: {subtract(a, b)}")
            
            elif choice.lower() == 'multiply':
                a = float(input("Enter first number: "))
                b = float(input("Enter second number: "))
                print(f"Result: {multiply(a, b)}")
            
            elif choice.lower() == 'divide':
                a = float(input("Enter first number: "))
                b = float(input("Enter second number: "))
                print(f"Result: {divide(a, b)}")
            
            elif choice.lower() == 'power':
                base = float(input("Enter base: "))
                exp = float(input("Enter exponent: "))
                print(f"Result: {power(base, exp)}")
            
            elif choice.lower() == 'calculate':
                expr = input("Enter expression: ")
                print(f"Result: {calculate(expr)}")
            
            else:
                print("Unknown operation. Try 'add', 'subtract', 'multiply', 'divide', 'power', or 'calculate'")
            
            print()
            
        except ValueError as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")

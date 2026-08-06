#!/usr/bin/env python3
"""
CLI interface for the calculator.
"""

import argparse
import sys
from calculator import Calculator, CalculatorError, DivisionByZeroError, InvalidOperationError


def format_result(result: float) -> str:
    """Format a numeric result for display."""
    if isinstance(result, float):
        # Check if it's a whole number
        if result.is_integer():
            return str(int(result))
        # Limit decimal places to avoid floating point artifacts
        return f"{result:.10g}"
    return str(result)


def interactive_mode():
    """Run the calculator in interactive mode."""
    calc = Calculator()
    print("=" * 50)
    print("Welcome to Python Calculator!")
    print("Type 'quit' or 'exit' to exit.")
    print("Type 'help' for available commands.")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input(">>> ").strip()
            
            if not user_input:
                continue
            
            # Handle quit commands
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break
            
            # Handle help command
            if user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("  + a b      Add a and b")
                print("  - a b      Subtract b from a")
                print("  * a b      Multiply a and b")
                print("  / a b      Divide a by b")
                print("  ** a b     Raise a to the power of b")
                print("  % a b      Modulo a by b")
                print("  eval expr  Evaluate an expression (e.g., '2 + 3 * 4')")
                print("  quit       Exit the calculator")
                print()
                continue
            
            # Parse the input
            parts = user_input.split()
            
            if len(parts) == 0:
                continue
            
            if len(parts) == 1:
                # Single operand - not supported
                print("Error: Please provide two operands or a complete expression.")
                continue
            
            if len(parts) == 2:
                # Binary operation
                try:
                    a = float(parts[0])
                    b = float(parts[1])
                except ValueError:
                    print(f"Error: Invalid numbers: {parts[0]} and {parts[1]}")
                    continue
                
                # Determine operation from first part
                if parts[0] == '+':
                    result = calc.add(a, b)
                    print(f"{a} + {b} = {format_result(result)}")
                elif parts[0] == '-':
                    result = calc.subtract(a, b)
                    print(f"{a} - {b} = {format_result(result)}")
                elif parts[0] == '*':
                    result = calc.multiply(a, b)
                    print(f"{a} × {b} = {format_result(result)}")
                elif parts[0] == '/':
                    try:
                        result = calc.divide(a, b)
                        print(f"{a} ÷ {b} = {format_result(result)}")
                    except DivisionByZeroError as e:
                        print(f"Error: {e}")
                elif parts[0] == '**':
                    result = calc.power(a, b)
                    print(f"{a} ** {b} = {format_result(result)}")
                elif parts[0] == '%':
                    try:
                        result = calc.modulo(a, b)
                        print(f"{a} % {b} = {format_result(result)}")
                    except DivisionByZeroError as e:
                        print(f"Error: {e}")
                else:
                    print(f"Error: Unknown operator: {parts[0]}")
            
            elif len(parts) > 2:
                # Expression evaluation
                expr = ' '.join(parts)
                try:
                    result = calc.evaluate(expr)
                    print(f"{expr} = {format_result(result)}")
                except (DivisionByZeroError, InvalidOperationError) as e:
                    print(f"Error: {e}")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def main():
    """Main entry point for the CLI calculator."""
    parser = argparse.ArgumentParser(
        description="A simple Python CLI calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculator.py add 5 3
  python calculator.py subtract 10 4
  python calculator.py multiply 6 7
  python calculator.py divide 20 4
  python calculator.py power 2 8
  python calculator.py modulo 17 5
  python calculator.py evaluate "2 + 3 * 4"
  python calculator.py -i  # Interactive mode
        """
    )
    
    parser.add_argument(
        'operation',
        choices=['add', 'subtract', 'multiply', 'divide', 'power', 'modulo', 'evaluate'],
        help='Operation to perform'
    )
    
    parser.add_argument(
        'args',
        nargs='*',
        help='Arguments for the operation (e.g., two numbers for add/subtract)'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    # Handle command-line operations
    calc = Calculator()
    
    if args.operation == 'add':
        if len(args.args) != 2:
            print("Error: add requires two numbers")
            sys.exit(1)
        try:
            a = float(args.args[0])
            b = float(args.args[1])
            result = calc.add(a, b)
            print(f"{a} + {b} = {format_result(result)}")
        except ValueError:
            print("Error: Invalid numbers provided")
            sys.exit(1)
    
    elif args.operation == 'subtract':
        if len(args.args) != 2:
            print("Error: subtract requires two numbers")
            sys.exit(1)
        try:
            a = float(args.args[0])
            b = float(args.args[1])
            result = calc.subtract(a, b)
            print(f"{a} - {b} = {format_result(result)}")
        except ValueError:
            print("Error: Invalid numbers provided")
            sys.exit(1)
    
    elif args.operation == 'multiply':
        if len(args.args) != 2:
            print("Error: multiply requires two numbers")
            sys.exit(1)
        try:
            a = float(args.args[0])
            b = float(args.args[1])
            result = calc.multiply(a, b)
            print(f"{a} × {b} = {format_result(result)}")
        except ValueError:
            print("Error: Invalid numbers provided")
            sys.exit(1)
    
    elif args.operation == 'divide':
        if len(args.args) != 2:
            print("Error: divide requires two numbers")
            sys.exit(1)
        try:
            a = float(args.args[0])
            b = float(args.args[1])
            result = calc.divide(a, b)
            print(f"{a} ÷ {b} = {format_result(result)}")
        except ValueError:
            print("Error: Invalid numbers provided")
            sys.exit(1)
        except DivisionByZeroError:
            print("Error: Cannot divide by zero")
            sys.exit(1)
    
    elif args.operation == 'power':
        if len(args.args) != 2:
            print("Error: power requires two numbers")
            sys.exit(1)
        try:
            base = float(args.args[0])
            exponent = float(args.args[1])
            result = calc.power(base, exponent)
            print(f"{base} ** {exponent} = {format_result(result)}")
        except ValueError:
            print("Error: Invalid numbers provided")
            sys.exit(1)
    
    elif args.operation == 'modulo':
        if len(args.args) != 2:
            print("Error: modulo requires two numbers")
            sys.exit(1)
        try:
            a = float(args.args[0])
            b = float(args.args[1])
            result = calc.modulo(a, b)
            print(f"{a} % {b} = {format_result(result)}")
        except ValueError:
            print("Error: Invalid numbers provided")
            sys.exit(1)
        except DivisionByZeroError:
            print("Error: Cannot compute modulo with zero
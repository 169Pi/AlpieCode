"""
Command-line interface for the calculator.
"""

import sys
from calculator import Calculator, CalculatorError, DivisionByZeroError, InvalidInputError


def print_help():
    """Print help message."""
    help_text = """
Calculator CLI - A simple command-line calculator

Usage:
    calculator <command> [arguments]

Commands:
    add <a> <b>              Add two numbers (a + b)
    sub <a> <b>              Subtract (a - b)
    mul <a> <b>              Multiply (a * b)
    div <a> <b>              Divide (a / b)
    pow <base> <exponent>    Power (base ^ exponent)
    mod <a> <b>              Modulo (a % b)
    sqrt <x>                 Square root of x
    fact <n>                 Factorial of n
    sin <x>                  Sine of x (radians)
    cos <x>                  Cosine of x (radians)
    tan <x>                  Tangent of x (radians)
    log <x> [base]           Logarithm of x (base 10 by default)
    abs <x>                  Absolute value of x
    help                     Show this help message

Examples:
    calculator add 5 3
    calculator div 10 2
    calculator pow 2 8
    calculator sqrt 16
    calculator fact 5
    calculator sin 1.57
    calculator log 100
    calculator log 100 2

"""
    print(help_text)


def parse_args(args: list) -> tuple:
    """Parse command line arguments.
    
    Args:
        args: List of command line arguments (without program name)
        
    Returns:
        Tuple of (command, *arguments)
    """
    if not args:
        return None, []
    
    command = args[0].lower()
    arguments = args[1:] if len(args) > 1 else []
    return command, arguments


def run_command(command: str, arguments: list) -> None:
    """Run a calculator command.
    
    Args:
        command: Command to run
        arguments: Arguments for the command
        
    Raises:
        SystemExit: If command is not found or arguments are invalid
    """
    calculator = Calculator()
    
    if command == "add":
        if len(arguments) != 2:
            print("Error: add requires 2 arguments", file=sys.stderr)
            print("Usage: calculator add <a> <b>", file=sys.stderr)
            sys.exit(1)
        try:
            a = float(arguments[0])
            b = float(arguments[1])
            result = calculator.add(a, b)
            print(f"{a} + {b} = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "sub":
        if len(arguments) != 2:
            print("Error: sub requires 2 arguments", file=sys.stderr)
            print("Usage: calculator sub <a> <b>", file=sys.stderr)
            sys.exit(1)
        try:
            a = float(arguments[0])
            b = float(arguments[1])
            result = calculator.subtract(a, b)
            print(f"{a} - {b} = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "mul":
        if len(arguments) != 2:
            print("Error: mul requires 2 arguments", file=sys.stderr)
            print("Usage: calculator mul <a> <b>", file=sys.stderr)
            sys.exit(1)
        try:
            a = float(arguments[0])
            b = float(arguments[1])
            result = calculator.multiply(a, b)
            print(f"{a} * {b} = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "div":
        if len(arguments) != 2:
            print("Error: div requires 2 arguments", file=sys.stderr)
            print("Usage: calculator div <a> <b>", file=sys.stderr)
            sys.exit(1)
        try:
            a = float(arguments[0])
            b = float(arguments[1])
            result = calculator.divide(a, b)
            print(f"{a} / {b} = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except DivisionByZeroError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "pow":
        if len(arguments) != 2:
            print("Error: pow requires 2 arguments", file=sys.stderr)
            print("Usage: calculator pow <base> <exponent>", file=sys.stderr)
            sys.exit(1)
        try:
            base = float(arguments[0])
            exponent = float(arguments[1])
            result = calculator.power(base, exponent)
            print(f"{base} ^ {exponent} = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "mod":
        if len(arguments) != 2:
            print("Error: mod requires 2 arguments", file=sys.stderr)
            print("Usage: calculator mod <a> <b>", file=sys.stderr)
            sys.exit(1)
        try:
            a = float(arguments[0])
            b = float(arguments[1])
            result = calculator.modulo(a, b)
            print(f"{a} % {b} = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except DivisionByZeroError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "sqrt":
        if len(arguments) != 1:
            print("Error: sqrt requires 1 argument", file=sys.stderr)
            print("Usage: calculator sqrt <x>", file=sys.stderr)
            sys.exit(1)
        try:
            x = float(arguments[0])
            result = calculator.sqrt(x)
            print(f"sqrt({x}) = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except InvalidInputError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "fact":
        if len(arguments) != 1:
            print("Error: fact requires 1 argument", file=sys.stderr)
            print("Usage: calculator fact <n>", file=sys.stderr)
            sys.exit(1)
        try:
            n = int(arguments[0])
            result = calculator.factorial(n)
            print(f"fact({n}) = {result}")
        except ValueError:
            print("Error: Invalid integer format", file=sys.stderr)
            sys.exit(1)
        except InvalidInputError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "sin":
        if len(arguments) != 1:
            print("Error: sin requires 1 argument", file=sys.stderr)
            print("Usage: calculator sin <x>", file=sys.stderr)
            sys.exit(1)
        try:
            x = float(arguments[0])
            result = calculator.sin(x)
            print(f"sin({x}) = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "cos":
        if len(arguments) != 1:
            print("Error: cos requires 1 argument", file=sys.stderr)
            print("Usage: calculator cos <x>", file=sys.stderr)
            sys.exit(1)
        try:
            x = float(arguments[0])
            result = calculator.cos(x)
            print(f"cos({x}) = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "tan":
        if len(arguments) != 1:
            print("Error: tan requires 1 argument", file=sys.stderr)
            print("Usage: calculator tan <x>", file=sys.stderr)
            sys.exit(1)
        try:
            x = float(arguments[0])
            result = calculator.tan(x)
            print(f"tan({x}) = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "log":
        if len(arguments) < 1:
            print("Error: log requires at least 1 argument", file=sys.stderr)
            print("Usage: calculator log <x> [base]", file=sys.stderr)
            sys.exit(1)
        try:
            x = float(arguments[0])
            base = float(arguments[1]) if len(arguments) > 1 else 10
            result = calculator.log(x, base)
            print(f"log({x}, {base}) = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except InvalidInputError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "abs":
        if len(arguments) != 1:
            print("Error: abs requires 1 argument", file=sys.stderr)
            print("Usage: calculator abs <x>", file=sys.stderr)
            sys.exit(1)
        try:
            x = float(arguments[0])
            result = calculator.abs(x)
            print(f"abs({x}) = {result}")
        except ValueError:
            print("Error: Invalid number format", file=sys.stderr)
            sys.exit(1)
        except CalculatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif command == "help":
        print_help()
        
    else:
        print(f"Error: Unknown command '{command}'", file=sys.stderr)
        print("Use 'calculator help' for usage information.", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command, arguments = parse_args(sys.argv[1:])
    run_command(command, arguments)


if __name__ == "__main__":
    main()
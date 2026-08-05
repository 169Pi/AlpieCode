#!/usr/bin/env python3
"""
CLI Calculator Module

A command-line calculator that supports basic arithmetic operations:
- add: Addition
- sub: Subtraction
- mul: Multiplication
- div: Division
- pow: Power
- mod: Modulo
- sqrt: Square root
- abs: Absolute value
"""

import math
import sys
from typing import Union


class Calculator:
    """A simple calculator class supporting basic arithmetic operations."""
    
    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Add two numbers."""
        return a + b
    
    def sub(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtract two numbers."""
        return a - b
    
    def mul(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiply two numbers."""
        return a * b
    
    def div(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return a / b
    
    def pow(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Raise a to the power of b."""
        return a ** b
    
    def mod(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Return the remainder of division."""
        if b == 0:
            raise ValueError("Modulo by zero is not allowed.")
        return a % b
    
    def sqrt(self, a: Union[int, float]) -> float:
        """Return the square root of a number."""
        if a < 0:
            raise ValueError("Cannot calculate square root of a negative number.")
        return math.sqrt(a)
    
    def abs(self, a: Union[int, float]) -> Union[int, float]:
        """Return the absolute value of a number."""
        return abs(a)
    
    def log(self, a: Union[int, float], base: Union[int, float] = 10) -> float:
        """Return the logarithm of a number with the specified base."""
        if a <= 0:
            raise ValueError("Logarithm of a non-positive number is not allowed.")
        return math.log(a, base)
    
    def sin(self, a: float) -> float:
        """Return the sine of an angle (in radians)."""
        return math.sin(a)
    
    def cos(self, a: float) -> float:
        """Return the cosine of an angle (in radians)."""
        return math.cos(a)
    
    def tan(self, a: float) -> float:
        """Return the tangent of an angle (in radians)."""
        return math.tan(a)
    
    def tanh(self, a: float) -> float:
        """Return the hyperbolic tangent of a number."""
        return math.tanh(a)
    
    def exp(self, a: float) -> float:
        """Return the exponential of a number."""
        return math.exp(a)
    
    def ln(self, a: Union[int, float]) -> float:
        """Return the natural logarithm of a number."""
        if a <= 0:
            raise ValueError("Natural logarithm of a non-positive number is not allowed.")
        return math.log(a)
    
    def factorial(self, n: int) -> int:
        """Return the factorial of a non-negative integer."""
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers.")
        return math.factorial(n)
    
    def gcd(self, a: int, b: int) -> int:
        """Return the greatest common divisor of two integers."""
        return math.gcd(a, b)
    
    def lcm(self, a: int, b: int) -> int:
        """Return the least common multiple of two integers."""
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // self.gcd(a, b)
    
    def min(self, *args: Union[int, float]) -> Union[int, float]:
        """Return the minimum of the given numbers."""
        return min(args)
    
    def max(self, *args: Union[int, float]) -> Union[int, float]:
        """Return the maximum of the given numbers."""
        return max(args)
    
    def sum(self, *args: Union[int, float]) -> Union[int, float]:
        """Return the sum of the given numbers."""
        return sum(args)
    
    def mean(self, *args: Union[int, float]) -> float:
        """Return the mean (average) of the given numbers."""
        return sum(args) / len(args) if args else 0
    
    def median(self, *args: Union[int, float]) -> float:
        """Return the median of the given numbers."""
        sorted_args = sorted(args)
        n = len(sorted_args)
        if n % 2 == 0:
            return (sorted_args[n // 2 - 1] + sorted_args[n // 2]) / 2
        return sorted_args[n // 2]
    
    def std(self, *args: Union[int, float]) -> float:
        """Return the standard deviation of the given numbers."""
        if len(args) < 2:
            return 0.0
        mean_val = self.mean(*args)
        variance = sum((x - mean_val) ** 2 for x in args) / len(args)
        return math.sqrt(variance)
    
    def variance(self, *args: Union[int, float]) -> float:
        """Return the variance of the given numbers."""
        if len(args) < 2:
            return 0.0
        mean_val = self.mean(*args)
        return sum((x - mean_val) ** 2 for x in args) / len(args)
    
    def minmax(self, *args: Union[int, float]) -> tuple:
        """Return a tuple of (min, max) of the given numbers."""
        return (self.min(*args), self.max(*args))
    
    def minmaxsum(self, *args: Union[int, float]) -> tuple:
        """Return a tuple of (min, max, sum) of the given numbers."""
        return (self.min(*args), self.max(*args), self.sum(*args))
    
    def minmaxmean(self, *args: Union[int, float]) -> tuple:
        """Return a tuple of (min, max, mean) of the given numbers."""
        return (self.min(*args), self.max(*args), self.mean(*args))
    
    def minmaxmeanstd(self, *args: Union[int, float]) -> tuple:
        """Return a tuple of (min, max, mean, std) of the given numbers."""
        return (self.min(*args), self.max(*args), self.mean(*args), self.std(*args))


def main():
    """Main function to run the CLI calculator."""
    calc = Calculator()
    
    if len(sys.argv) < 2:
        print("Usage: python calculator.py <operation> <args...>")
        print("Operations:")
        print("  add <a> <b>                    - Addition")
        print("  sub <a> <b>                    - Subtraction")
        print("  mul <a> <b>                    - Multiplication")
        print("  div <a> <b>                    - Division")
        print("  pow <a> <b>                    - Power (a^b)")
        print("  mod <a> <b>                    - Modulo")
        print("  sqrt <a>                       - Square root")
        print("  abs <a>                        - Absolute value")
        print("  log <a> [base]                 - Logarithm")
        print("  sin <a>                        - Sine")
        print("  cos <a>                        - Cosine")
        print("  tan <a>                        - Tangent")
        print("  tanh <a>                       - Hyperbolic tangent")
        print("  exp <a>                        - Exponential")
        print("  ln <a>                         - Natural logarithm")
        print("  factorial <n>                  - Factorial")
        print("  gcd <a> <b>                    - Greatest common divisor")
        print("  lcm <a> <b>                    - Least common multiple")
        print("  min <a> <b> ...               - Minimum")
        print("  max <a> <b> ...               - Maximum")
        print("  sum <a> <b> ...               - Sum")
        print("  mean <a> <b> ...              - Mean")
        print("  median <a> <b> ...            - Median")
        print("  std <a> <b> ...               - Standard deviation")
        print("  variance <a> <b> ...          - Variance")
        print("  minmax <a> <b> ...            - Min and Max")
        print("  minmaxsum <a> <b> ...         - Min, Max, Sum")
        print("  minmaxmean <a> <b> ...        - Min, Max, Mean")
        print("  minmaxmeanstd <a> <b> ...     - Min, Max, Mean, Std")
        print("  help                           - Show this help message")
        return
    
    if sys.argv[1] == "help":
        print("Usage: python calculator.py <operation> <args...>")
        print("Operations:")
        print("  add <a> <b>                    - Addition")
        print("  sub <a> <b>                    - Subtraction")
        print("  mul <a> <b>                    - Multiplication")
        print("  div <a> <b>                    - Division")
        print("  pow <a> <b>                    - Power (a^b)")
        print("  mod <a> <b>                    - Modulo")
        print("  sqrt <a>                       - Square root")
        print("  abs <a>                        - Absolute value")
        print("  log <a> [base]                 - Logarithm")
        print("  sin <a>                        - Sine")
        print("  cos <a>                        - Cosine")
        print("  tan <a>                        - Tangent")
        print("  tanh <a>                       - Hyperbolic tangent")
        print("  exp <a>                        - Exponential")
        print("  ln <a>                         - Natural logarithm")
        print("  factorial <n>                  - Factorial")
        print("  gcd <a> <b>                    - Greatest common divisor")
        print("  lcm <a> <b>                    - Least common multiple")
        print("  min <a> <b> ...               - Minimum")
        print("  max <a> <b> ...               - Maximum")
        print("  sum <a> <b> ...               - Sum")
        print("  mean <a> <b> ...              - Mean")
        print("  median <a> <b> ...            - Median")
        print("  std <a> <b> ...               - Standard deviation")
        print("  variance <a> <b> ...          - Variance")
        print("  minmax <a> <b> ...            - Min and Max")
        print("  minmaxsum <a> <b> ...         - Min, Max, Sum")
        print("  minmaxmean <a> <b> ...        - Min, Max, Mean")
        print("  minmaxmeanstd <a> <b> ...     - Min, Max, Mean, Std")
        print("  help                           - Show this help message")
        return
    
    operation = sys.argv[1]
    
    try:
        if operation == "add":
            a = float(sys.argv[2])
            b = float(sys.argv[3])
            result = calc.add(a, b)
            print(f"{a} + {b} = {result}")
        
        elif operation == "sub":
            a = float(sys.argv[2])
            b = float(sys.argv[3])
            result = calc.sub(a, b)
            print(f"{a} - {b} = {result}")
        
        elif operation == "mul":
            a = float(sys.argv[2])
            b = float(sys.argv[3])
            result = calc.mul(a, b)
            print(f"{a} * {b} = {result}")
        
        elif operation == "div":
            a = float(sys.argv[2])
            b = float(sys.argv[3])
            result = calc.div(a, b)
            print(f"{a} / {b} = {result}")
        
        elif operation == "pow":
            a = float(sys.argv[2])
            b = float(sys.argv[3])
            result = calc.pow(a, b)
            print(f"{a} ** {b} = {result}")
        
        elif operation == "mod":
            a = float(sys.argv[2])
            b = float(sys.argv[3])
            result = calc.mod(a, b)
            print(f"{a} % {b} = {result}")
        
        elif operation == "sqrt":
            a = float(sys.argv[2])
            result = calc.sqrt(a)
            print(f"sqrt({a}) = {result}")
        
        elif operation == "abs":
            a = float(sys.argv[2])
            result = calc.abs(a)
            print(f"abs({a}) = {result}")
        
        elif operation == "log":
            a = float(sys.argv[2])
            base = float(sys.argv[3]) if len(sys.argv) > 3 else 10
            result = calc.log(a, base)
            print(f"log({a}, {base}) = {result}")
        
        elif operation == "sin":
            a = float(sys.argv[2])
            result = calc.sin(a)
            print(f"sin({a}) = {result}")
        
        elif operation == "cos":
            a = float(sys.argv[2])
            result = calc.cos(a)
            print(f"cos({a}) = {result}")
        
        elif operation == "tan":
            a = float(sys.argv[2])
            result = calc.tan(a)
            print(f"tan({a}) = {result}")
        
        elif operation == "tanh":
            a = float(sys.argv[2])
            result = calc.tanh(a)
            print(f"tanh({a}) = {result}")
        
        elif operation == "exp":
            a = float(sys.argv[2])
            result = calc.exp(a)
            print(f"exp({a}) = {result}")
        
        elif operation == "ln":
            a = float(sys.argv[2])
            result = calc.ln(a)
            print(f"ln({a}) = {result}")
        
        elif operation == "factorial":
            n = int(sys.argv[2])
            result = calc.factorial(n)
            print(f"factorial({n}) = {result}")
        
        elif operation == "gcd":
            a = int(sys.argv[2])
            b = int(sys.argv[3])
            result = calc.gcd(a, b)
            print(f"gcd({a}, {b}) = {result}")
        
        elif operation == "lcm":
            a = int(sys.argv[2])
            b = int(sys.argv[3])
            result = calc.lcm(a, b)
            print(f"lcm({a}, {b}) = {result}")
        
        elif operation == "min":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.min(*args)
            print(f"min({', '.join(map(str, args))}) = {result}")
        
        elif operation == "max":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.max(*args)
            print(f"max({', '.join(map(str, args))}) = {result}")
        
        elif operation == "sum":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.sum(*args)
            print(f"sum({', '.join(map(str, args))}) = {result}")
        
        elif operation == "mean":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.mean(*args)
            print(f"mean({', '.join(map(str, args))}) = {result}")
        
        elif operation == "median":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.median(*args)
            print(f"median({', '.join(map(str, args))}) = {result}")
        
        elif operation == "std":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.std(*args)
            print(f"std({', '.join(map(str, args))}) = {result}")
        
        elif operation == "variance":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.variance(*args)
            print(f"variance({', '.join(map(str, args))}) = {result}")
        
        elif operation == "minmax":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.minmax(*args)
            print(f"minmax({', '.join(map(str, args))}) = {result}")
        
        elif operation == "minmaxsum":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.minmaxsum(*args)
            print(f"minmaxsum({', '.join(map(str, args))}) = {result}")
        
        elif operation == "minmaxmean":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.minmaxmean(*args)
            print(f"minmaxmean({', '.join(map(str, args))}) = {result}")
        
        elif operation == "minmaxmeanstd":
            args = [float(arg) for arg in sys.argv[2:]]
            result = calc.minmaxmeanstd(*args)
            print(f"minmaxmeanstd({', '.join(map(str, args))}) = {result}")
        
        else:
            print(f"Unknown operation: {operation}")
            print("Use 'help' to see available operations.")
            sys.exit(1)
    
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
"""
Fibonacci number utilities.

This module provides multiple methods to generate and work with Fibonacci numbers.
"""


def fibonacci_iterative(n: int) -> int:
    """
    Calculate the nth Fibonacci number using an iterative approach.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
        
    Examples:
        >>> fibonacci_iterative(0)
        0
        >>> fibonacci_iterative(1)
        1
        >>> fibonacci_iterative(10)
        55
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    
    return curr


def fibonacci_recursive(n: int, memo: dict = None) -> int:
    """
    Calculate the nth Fibonacci number using recursion with memoization.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        memo: Optional dictionary for memoization (created if not provided)
        
    Returns:
        The nth Fibonacci number
        
    Examples:
        >>> fibonacci_recursive(0)
        0
        >>> fibonacci_recursive(10)
        55
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    
    if memo is None:
        memo = {}
    
    if n in memo:
        return memo[n]
    
    if n == 0:
        result = 0
    elif n == 1:
        result = 1
    else:
        result = fibonacci_recursive(n - 1, memo) + fibonacci_recursive(n - 2, memo)
    
    memo[n] = result
    return result


def fibonacci_generator(count: int):
    """
    Generate Fibonacci numbers as a generator.
    
    Args:
        count: Number of Fibonacci numbers to generate
        
    Yields:
        Fibonacci numbers in sequence
        
    Examples:
        >>> list(fibonacci_generator(5))
        [0, 1, 1, 2, 3]
    """
    if count <= 0:
        return
    
    a, b = 0, 1
    for _ in range(count):
        yield a
        a, b = b, a + b


def is_fibonacci(n: int) -> bool:
    """
    Check if a number is a Fibonacci number.
    
    A number is Fibonacci if and only if one or both of (5*n^2 + 4) or (5*n^2 - 4) is a perfect square.
    
    Args:
        n: The number to check
        
    Returns:
        True if n is a Fibonacci number, False otherwise
        
    Examples:
        >>> is_fibonacci(0)
        True
        >>> is_fibonacci(1)
        True
        >>> is_fibonacci(8)
        True
        >>> is_fibonacci(10)
        False
    """
    if n < 0:
        return False
    
    def is_perfect_square(x):
        """Check if x is a perfect square."""
        if x < 0:
            return False
        sqrt = int(x ** 0.5)
        return sqrt * sqrt == x
    
    return is_perfect_square(5 * n * n + 4) or is_perfect_square(5 * n * n - 4)


def fibonacci_sequence(n: int) -> list:
    """
    Generate a list of the first n Fibonacci numbers.
    
    Args:
        n: Number of Fibonacci numbers to generate
        
    Returns:
        List of the first n Fibonacci numbers
        
    Examples:
        >>> fibonacci_sequence(5)
        [0, 1, 1, 2, 3]
    """
    return list(fibonacci_generator(n))


if __name__ == "__main__":
    # Demo usage
    print("Fibonacci Number Utilities")
    print("=" * 40)
    
    # Show first 10 Fibonacci numbers
    print("\nFirst 10 Fibonacci numbers:")
    for i, num in enumerate(fibonacci_sequence(10)):
        print(f"  F({i}) = {num}")
    
    # Test is_fibonacci function
    print("\nTesting is_fibonacci():")
    test_numbers = [0, 1, 2, 3, 5, 8, 13, 21, 34, 42, 100]
    for num in test_numbers:
        print(f"  {num}: {'Yes' if is_fibonacci(num) else 'No'}")
    
    # Test with larger number
    print(f"\nF(20) = {fibonacci_iterative(20)}")
    print(f"F(50) = {fibonacci_iterative(50)}")

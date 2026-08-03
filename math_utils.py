"""Math utilities module."""


def fibonacci(n: int) -> int:
    """
    Return the nth Fibonacci number.

    Args:
        n: The position in the Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(5)
        5
        >>> fibonacci(10)
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

"""Tests for math_utils module."""

import pytest
from math_utils import fibonacci


class TestFibonacci:
    """Test cases for the fibonacci function."""

    def test_fibonacci_0(self):
        """Test fibonacci(0) returns 0."""
        assert fibonacci(0) == 0

    def test_fibonacci_1(self):
        """Test fibonacci(1) returns 1."""
        assert fibonacci(1) == 1

    def test_fibonacci_2(self):
        """Test fibonacci(2) returns 1."""
        assert fibonacci(2) == 1

    def test_fibonacci_5(self):
        """Test fibonacci(5) returns 5."""
        assert fibonacci(5) == 5

    def test_fibonacci_10(self):
        """Test fibonacci(10) returns 55."""
        assert fibonacci(10) == 55

    def test_fibonacci_20(self):
        """Test fibonacci(20) returns 6765."""
        assert fibonacci(20) == 6765

    def test_fibonacci_negative(self):
        """Test fibonacci raises ValueError for negative input."""
        with pytest.raises(ValueError):
            fibonacci(-1)

    def test_fibonacci_large(self):
        """Test fibonacci with larger input."""
        assert fibonacci(50) == 12586269025

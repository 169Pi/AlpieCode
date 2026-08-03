"""Tests for math_utils module."""

import pytest
from math_utils import fibonacci


class TestFibonacci:
    """Test cases for the fibonacci function."""

    def test_fibonacci_zero(self):
        """Test that fibonacci(0) returns 0."""
        assert fibonacci(0) == 0

    def test_fibonacci_one(self):
        """Test that fibonacci(1) returns 1."""
        assert fibonacci(1) == 1

    def test_fibonacci_two(self):
        """Test that fibonacci(2) returns 1."""
        assert fibonacci(2) == 1

    def test_fibonacci_ten(self):
        """Test that fibonacci(10) returns 55."""
        assert fibonacci(10) == 55

    def test_fibonacci_fifty(self):
        """Test that fibonacci(50) returns correct value."""
        assert fibonacci(50) == 12586269025

    def test_fibonacci_negative(self):
        """Test that negative input raises ValueError."""
        with pytest.raises(ValueError):
            fibonacci(-1)

    def test_fibonacci_large(self):
        """Test fibonacci with a larger input."""
        assert fibonacci(100) == 354224848179261915075

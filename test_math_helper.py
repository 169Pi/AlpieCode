"""Unit tests for math_helper module."""

import unittest
from math_helper import add, subtract, multiply


class TestAdd(unittest.TestCase):
    """Tests for the add function."""

    def test_add_positive_numbers(self):
        """Test adding two positive numbers."""
        self.assertEqual(add(2, 3), 5)

    def test_add_negative_numbers(self):
        """Test adding two negative numbers."""
        self.assertEqual(add(-2, -3), -5)

    def test_add_mixed_numbers(self):
        """Test adding positive and negative numbers."""
        self.assertEqual(add(-2, 3), 1)

    def test_add_floats(self):
        """Test adding floating point numbers."""
        self.assertAlmostEqual(add(0.1, 0.2), 0.3, places=10)

    def test_add_zero(self):
        """Test adding zero."""
        self.assertEqual(add(0, 5), 5)
        self.assertEqual(add(5, 0), 5)


class TestSubtract(unittest.TestCase):
    """Tests for the subtract function."""

    def test_subtract_positive_numbers(self):
        """Test subtracting two positive numbers."""
        self.assertEqual(subtract(5, 3), 2)

    def test_subtract_negative_numbers(self):
        """Test subtracting two negative numbers."""
        self.assertEqual(subtract(-5, -3), -2)

    def test_subtract_mixed_numbers(self):
        """Test subtracting positive from negative."""
        self.assertEqual(subtract(-5, 3), -8)

    def test_subtract_floats(self):
        """Test subtracting floating point numbers."""
        self.assertAlmostEqual(subtract(1.5, 0.5), 1.0, places=10)

    def test_subtract_zero(self):
        """Test subtracting zero."""
        self.assertEqual(subtract(5, 0), 5)
        self.assertEqual(subtract(0, 5), -5)


class TestMultiply(unittest.TestCase):
    """Tests for the multiply function."""

    def test_multiply_positive_numbers(self):
        """Test multiplying two positive numbers."""
        self.assertEqual(multiply(2, 3), 6)

    def test_multiply_negative_numbers(self):
        """Test multiplying two negative numbers."""
        self.assertEqual(multiply(-2, -3), 6)

    def test_multiply_mixed_numbers(self):
        """Test multiplying positive and negative numbers."""
        self.assertEqual(multiply(-2, 3), -6)

    def test_multiply_floats(self):
        """Test multiplying floating point numbers."""
        self.assertAlmostEqual(multiply(0.5, 0.4), 0.2, places=10)

    def test_multiply_by_zero(self):
        """Test multiplying by zero."""
        self.assertEqual(multiply(5, 0), 0)
        self.assertEqual(multiply(0, 5), 0)


if __name__ == '__main__':
    unittest.main()
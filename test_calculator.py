"""
Unit tests for the Python CLI Calculator.

Tests all arithmetic operations, edge cases, and CLI parsing.
"""

import pytest
from calculator import (
    add,
    subtract,
    multiply,
    divide,
    calculate,
)


class TestAdd:
    """Tests for the add function."""
    
    def test_add_positive_integers(self):
        """Test adding positive integers."""
        assert add(2, 3) == 5
    
    def test_add_negative_integers(self):
        """Test adding negative integers."""
        assert add(-2, -3) == -5
    
    def test_add_mixed_integers(self):
        """Test adding positive and negative integers."""
        assert add(-2, 3) == 1
        assert add(2, -3) == -1
    
    def test_add_floats(self):
        """Test adding floating point numbers."""
        assert add(1.5, 2.5) == 4.0
        assert add(0.1, 0.2) == 0.3
    
    def test_add_zero(self):
        """Test adding zero."""
        assert add(5, 0) == 5
        assert add(0, 5) == 5
    
    def test_add_large_numbers(self):
        """Test adding large numbers."""
        assert add(10**10, 10**10) == 2 * 10**10


class TestSubtract:
    """Tests for the subtract function."""
    
    def test_subtract_positive_integers(self):
        """Test subtracting positive integers."""
        assert subtract(5, 3) == 2
    
    def test_subtract_negative_integers(self):
        """Test subtracting negative integers."""
        assert subtract(-5, -3) == -2
    
    def test_subtract_mixed_integers(self):
        """Test subtracting positive and negative integers."""
        assert subtract(-2, 3) == -5
        assert subtract(2, -3) == 5
    
    def test_subtract_floats(self):
        """Test subtracting floating point numbers."""
        assert subtract(5.5, 2.5) == 3.0
        assert subtract(1.0, 0.5) == 0.5
    
    def test_subtract_zero(self):
        """Test subtracting zero."""
        assert subtract(5, 0) == 5
        assert subtract(0, 5) == -5


class TestMultiply:
    """Tests for the multiply function."""
    
    def test_multiply_positive_integers(self):
        """Test multiplying positive integers."""
        assert multiply(3, 4) == 12
    
    def test_multiply_negative_integers(self):
        """Test multiplying negative integers."""
        assert multiply(-3, -4) == 12
        assert multiply(-3, 4) == -12
    
    def test_multiply_floats(self):
        """Test multiplying floating point numbers."""
        assert multiply(2.5, 4.0) == 10.0
        assert multiply(0.5, 0.5) == 0.25
    
    def test_multiply_by_zero(self):
        """Test multiplying by zero."""
        assert multiply(5, 0) == 0
        assert multiply(0, 5) == 0
    
    def test_multiply_large_numbers(self):
        """Test multiplying large numbers."""
        assert multiply(1000, 1000) == 1000000


class TestDivide:
    """Tests for the divide function."""
    
    def test_divide_positive_integers(self):
        """Test dividing positive integers."""
        assert divide(10, 2) == 5.0
        assert divide(8, 4) == 2.0
    
    def test_divide_negative_integers(self):
        """Test dividing negative integers."""
        assert divide(-10, 2) == -5.0
        assert divide(10, -2) == -5.0
        assert divide(-10, -2) == 5.0
    
    def test_divide_floats(self):
        """Test dividing floating point numbers."""
        assert divide(7.0, 2.0) == 3.5
        assert divide(1.0, 3.0) == pytest.approx(0.3333333333)
    
    def test_divide_by_zero_raises_error(self):
        """Test that division by zero raises ValueError."""
        with pytest.raises(ValueError, match="Division by zero"):
            divide(10, 0)
        with pytest.raises(ValueError, match="Division by zero"):
            divide(0, 0)
    
    def test_divide_zero_by_number(self):
        """Test dividing zero by a number."""
        assert divide(0, 5) == 0.0


class TestCalculate:
    """Tests for the calculate function (CLI interface)."""
    
    def test_calculate_addition(self):
        """Test calculating addition."""
        assert calculate("2 + 3") == 5
        assert calculate("10 + 5") == 15
    
    def test_calculate_subtraction(self):
        """Test calculating subtraction."""
        assert calculate("10 - 3") == 7
        assert calculate("5 - 10") == -5
    
    def test_calculate_multiplication(self):
        """Test calculating multiplication."""
        assert calculate("3 * 4") == 12
        assert calculate("6 * 7") == 42
    
    def test_calculate_division(self):
        """Test calculating division."""
        assert calculate("10 / 2") == 5.0
        assert calculate("15 / 3") == 5.0
    
    def test_calculate_mixed_operations(self):
        """Test calculating mixed operations (order of operations)."""
        assert calculate("2 + 3 * 4") == 14  # 2 + 12 = 14
        assert calculate("(2 + 3) * 4") == 20  # 5 * 4 = 20
        assert calculate("10 - 2 * 3") == 4   # 10 - 6 = 4
    
    def test_calculate_with_spaces(self):
        """Test that spaces in expressions are handled."""
        assert calculate("  2  +  3  ") == 5
        assert calculate("10    -    5") == 5
    
    def test_calculate_negative_numbers(self):
        """Test calculating with negative numbers."""
        assert calculate("-2 + 3") == 1
        assert calculate("2 + -3") == -1
        assert calculate("-2 * -3") == 6
    
    def test_calculate_floats(self):
        """Test calculating with floating point numbers."""
        assert calculate("2.5 + 3.5") == 6.0
        assert calculate("10.5 / 2") == 5.25
    
    def test_calculate_division_by_zero(self):
        """Test that division by zero raises ValueError."""
        with pytest.raises(ValueError, match="Division by zero"):
            calculate("10 / 0")
        with pytest.raises(ValueError, match="Division by zero"):
            calculate("0 / 0")
    
    def test_calculate_invalid_expression(self):
        """Test that invalid expressions raise ValueError."""
        with pytest.raises(ValueError):
            calculate("2 + * 3")
        with pytest.raises(ValueError):
            calculate("2 + a + 3")
        with pytest.raises(ValueError):
            calculate("2 + 3 +")
        with pytest.raises(ValueError):
            calculate("")
    
    def test_calculate_parentheses(self):
        """Test calculating expressions with parentheses."""
        assert calculate("(2 + 3) * 4") == 20
        assert calculate("((2 + 3) * 4)") == 20
        assert calculate("2 * (3 + 4)") == 14
    
    def test_calculate_power_using_multiplication(self):
        """Test calculating power using repeated multiplication."""
        # Note: This calculator doesn't support ** operator
        # But we can test that it raises an error
        with pytest.raises(ValueError):
            calculate("2 ** 3")


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            calculate("")
    
    def test_whitespace_only(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError):
            calculate("   ")
    
    def test_invalid_characters(self):
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError):
            calculate("2 + a")
        with pytest.raises(ValueError):
            calculate("2 + 3 @ 4")
        with pytest.raises(ValueError):
            calculate("2 + 3 % 4")
    
    def test_single_number(self):
        """Test that a single number returns itself."""
        assert calculate("5") == 5
        assert calculate("3.14") == 3.14
    
    def test_multiple_operations(self):
        """Test multiple operations in sequence."""
        assert calculate("1 + 2 + 3 + 4") == 10
        assert calculate("10 - 2 - 3 - 4") == 1
        assert calculate("2 * 3 * 4") == 24
    
    def test_complex_expression(self):
        """Test a complex expression."""
        # (10 + 5) * (3 - 1) = 15 * 2 = 30
        assert calculate("(10 + 5) * (3 - 1)") == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Unit tests for the calculator module.
"""

import pytest
from calculator import Calculator, CalculatorError, DivisionByZeroError, InvalidOperationError


class TestCalculatorAddition:
    """Tests for the add operation."""
    
    def test_add_positive_numbers(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5
    
    def test_add_negative_numbers(self):
        calc = Calculator()
        assert calc.add(-2, -3) == -5
    
    def test_add_mixed_numbers(self):
        calc = Calculator()
        assert calc.add(-2, 3) == 1
    
    def test_add_floats(self):
        calc = Calculator()
        assert calc.add(1.5, 2.5) == 4.0
    
    def test_add_zero(self):
        calc = Calculator()
        assert calc.add(0, 5) == 5
        assert calc.add(5, 0) == 5
    
    def test_add_large_numbers(self):
        calc = Calculator()
        assert calc.add(10**10, 10**10) == 2 * 10**10
    
    def test_add_small_numbers(self):
        calc = Calculator()
        assert calc.add(0.001, 0.002) == 0.003


class TestCalculatorSubtraction:
    """Tests for the subtract operation."""
    
    def test_subtract_positive_numbers(self):
        calc = Calculator()
        assert calc.subtract(5, 3) == 2
    
    def test_subtract_negative_numbers(self):
        calc = Calculator()
        assert calc.subtract(-5, -3) == -2
    
    def test_subtract_mixed_numbers(self):
        calc = Calculator()
        assert calc.subtract(5, -3) == 8
        assert calc.subtract(-5, 3) == -8
    
    def test_subtract_floats(self):
        calc = Calculator()
        assert calc.subtract(5.5, 2.5) == 3.0
    
    def test_subtract_zero(self):
        calc = Calculator()
        assert calc.subtract(5, 0) == 5
        assert calc.subtract(0, 5) == -5
    
    def test_subtract_same_numbers(self):
        calc = Calculator()
        assert calc.subtract(5, 5) == 0


class TestCalculatorMultiplication:
    """Tests for the multiply operation."""
    
    def test_multiply_positive_numbers(self):
        calc = Calculator()
        assert calc.multiply(3, 4) == 12
    
    def test_multiply_negative_numbers(self):
        calc = Calculator()
        assert calc.multiply(-3, -4) == 12
    
    def test_multiply_mixed_numbers(self):
        calc = Calculator()
        assert calc.multiply(-3, 4) == -12
    
    def test_multiply_floats(self):
        calc = Calculator()
        assert calc.multiply(2.5, 4.0) == 10.0
    
    def test_multiply_by_zero(self):
        calc = Calculator()
        assert calc.multiply(5, 0) == 0
        assert calc.multiply(0, 5) == 0
    
    def test_multiply_large_numbers(self):
        calc = Calculator()
        assert calc.multiply(1000, 1000) == 1_000_000


class TestCalculatorDivision:
    """Tests for the divide operation."""
    
    def test_divide_positive_numbers(self):
        calc = Calculator()
        assert calc.divide(10, 2) == 5
    
    def test_divide_negative_numbers(self):
        calc = Calculator()
        assert calc.divide(-10, -2) == 5
    
    def test_divide_mixed_numbers(self):
        calc = Calculator()
        assert calc.divide(-10, 2) == -5
        assert calc.divide(10, -2) == -5
    
    def test_divide_floats(self):
        calc = Calculator()
        assert calc.divide(10.0, 3.0) == pytest.approx(3.3333333333)
    
    def test_divide_by_one(self):
        calc = Calculator()
        assert calc.divide(5, 1) == 5
    
    def test_divide_zero_by_number(self):
        calc = Calculator()
        assert calc.divide(0, 5) == 0
    
    def test_divide_by_zero_raises_error(self):
        calc = Calculator()
        with pytest.raises(DivisionByZeroError):
            calc.divide(5, 0)
    
    def test_divide_negative_by_zero_raises_error(self):
        calc = Calculator()
        with pytest.raises(DivisionByZeroError):
            calc.divide(-5, 0)


class TestCalculatorPower:
    """Tests for the power operation."""
    
    def test_power_positive_base_positive_exponent(self):
        calc = Calculator()
        assert calc.power(2, 3) == 8
    
    def test_power_negative_base_positive_exponent(self):
        calc = Calculator()
        assert calc.power(-2, 3) == -8
    
    def test_power_positive_base_negative_exponent(self):
        calc = Calculator()
        assert calc.power(2, -3) == pytest.approx(0.125)
    
    def test_power_negative_base_negative_exponent(self):
        calc = Calculator()
        assert calc.power(-2, -2) == pytest.approx(0.25)
    
    def test_power_zero_exponent(self):
        calc = Calculator()
        assert calc.power(5, 0) == 1
    
    def test_power_zero_base_positive_exponent(self):
        calc = Calculator()
        assert calc.power(0, 5) == 0
    
    def test_power_zero_base_zero_exponent(self):
        calc = Calculator()
        # 0^0 is typically defined as 1
        assert calc.power(0, 0) == 1
    
    def test_power_float_base(self):
        calc = Calculator()
        assert calc.power(2.5, 2) == pytest.approx(6.25)


class TestCalculatorModulo:
    """Tests for the modulo operation."""
    
    def test_modulo_positive_numbers(self):
        calc = Calculator()
        assert calc.modulo(10, 3) == 1
    
    def test_modulo_negative_numbers(self):
        calc = Calculator()
        assert calc.modulo(-10, 3) == 2
        assert calc.modulo(10, -3) == -2
        assert calc.modulo(-10, -3) == -2
    
    def test_modulo_by_one(self):
        calc = Calculator()
        assert calc.modulo(10, 1) == 0
    
    def test_modulo_by_zero_raises_error(self):
        calc = Calculator()
        with pytest.raises(DivisionByZeroError):
            calc.modulo(10, 0)


class TestCalculatorEvaluate:
    """Tests for the evaluate method."""
    
    def test_evaluate_simple_addition(self):
        calc = Calculator()
        assert calc.evaluate("2 + 3") == 5
    
    def test_evaluate_simple_subtraction(self):
        calc = Calculator()
        assert calc.evaluate("10 - 4") == 6
    
    def test_evaluate_simple_multiplication(self):
        calc = Calculator()
        assert calc.evaluate("6 * 7") == 42
    
    def test_evaluate_simple_division(self):
        calc = Calculator()
        assert calc.evaluate("20 / 4") == 5
    
    def test_evaluate_expression_with_precedence(self):
        calc = Calculator()
        assert calc.evaluate("2 + 3 * 4") == 14
    
    def test_evaluate_nested_parentheses(self):
        calc = Calculator()
        assert calc.evaluate("(2 + 3) * (4 - 1)") == 15
    
    def test_evaluate_power(self):
        calc = Calculator()
        assert calc.evaluate("2 ** 3") == 8
    
    def test_evaluate_modulo(self):
        calc = Calculator()
        assert calc.evaluate("17 % 5") == 2
    
    def test_evaluate_complex_expression(self):
        calc = Calculator()
        assert calc.evaluate("(10 + 5) * (20 - 8) / 6") == 35
    
    def test_evaluate_with_floats(self):
        calc = Calculator()
        assert calc.evaluate("1.5 + 2.5") == 4.0
    
    def test_evaluate_division_by_zero_raises_error(self):
        calc = Calculator()
        with pytest.raises(DivisionByZeroError):
            calc.evaluate("10 / 0")
    
    def test_evaluate_invalid_syntax_raises
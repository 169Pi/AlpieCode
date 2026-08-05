#!/usr/bin/env python3
"""
Unit tests for the calculator module.

Run with: python -m pytest test_calculator.py -v
"""

import pytest
import sys
from unittest.mock import patch
from calculator import Calculator, CalculatorError, parse_arguments, main


class TestCalculatorError:
    """Tests for the CalculatorError exception."""
    
    def test_calculator_error_is_exception(self):
        """Verify CalculatorError is a proper exception class."""
        with pytest.raises(CalculatorError):
            raise CalculatorError("Test error")
    
    def test_calculator_error_message(self):
        """Verify error message is preserved."""
        error = CalculatorError("Invalid number: 'abc'")
        assert str(error) == "Invalid number: 'abc'"


class TestCalculatorBasicOperations:
    """Tests for basic arithmetic operations."""
    
    def setup_method(self):
        """Set up a fresh calculator for each test."""
        self.calc = Calculator()
    
    def test_add_positive_numbers(self):
        """Test addition with positive numbers."""
        result = self.calc.add(2, 3)
        assert result == 5
    
    def test_add_negative_numbers(self):
        """Test addition with negative numbers."""
        result = self.calc.add(-2, -3)
        assert result == -5
    
    def test_add_mixed_numbers(self):
        """Test addition with mixed positive and negative numbers."""
        result = self.calc.add(-2, 5)
        assert result == 3
    
    def test_add_zeros(self):
        """Test addition with zeros."""
        result = self.calc.add(0, 0)
        assert result == 0
    
    def test_add_floats(self):
        """Test addition with floating point numbers."""
        result = self.calc.add(1.5, 2.5)
        assert result == 4.0
    
    def test_subtract_positive_numbers(self):
        """Test subtraction with positive numbers."""
        result = self.calc.subtract(10, 3)
        assert result == 7
    
    def test_subtract_negative_numbers(self):
        """Test subtraction with negative numbers."""
        result = self.calc.subtract(-10, -3)
        assert result == -7
    
    def test_subtract_mixed_numbers(self):
        """Test subtraction with mixed numbers."""
        result = self.calc.subtract(5, -3)
        assert result == 8
    
    def test_subtract_zeros(self):
        """Test subtraction with zeros."""
        result = self.calc.subtract(0, 0)
        assert result == 0
    
    def test_subtract_result_is_negative(self):
        """Test subtraction resulting in negative number."""
        result = self.calc.subtract(3, 10)
        assert result == -7
    
    def test_multiply_positive_numbers(self):
        """Test multiplication with positive numbers."""
        result = self.calc.multiply(4, 5)
        assert result == 20
    
    def test_multiply_negative_numbers(self):
        """Test multiplication with negative numbers."""
        result = self.calc.multiply(-4, -5)
        assert result == 20
    
    def test_multiply_mixed_numbers(self):
        """Test multiplication with mixed signs."""
        result = self.calc.multiply(-4, 5)
        assert result == -20
    
    def test_multiply_by_zero(self):
        """Test multiplication by zero."""
        result = self.calc.multiply(100, 0)
        assert result == 0
    
    def test_multiply_floats(self):
        """Test multiplication with floating point numbers."""
        result = self.calc.multiply(2.5, 4)
        assert result == 10.0
    
    def test_divide_positive_numbers(self):
        """Test division with positive numbers."""
        result = self.calc.divide(10, 2)
        assert result == 5.0
    
    def test_divide_negative_numbers(self):
        """Test division with negative numbers."""
        result = self.calc.divide(-10, -2)
        assert result == 5.0
    
    def test_divide_mixed_numbers(self):
        """Test division with mixed signs."""
        result = self.calc.divide(-10, 2)
        assert result == -5.0
    
    def test_divide_floats(self):
        """Test division resulting in float."""
        result = self.calc.divide(7, 2)
        assert result == 3.5
    
    def test_divide_by_zero_raises_error(self):
        """Test that division by zero raises CalculatorError."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc.divide(10, 0)
        assert "Division by zero" in str(exc_info.value)


class TestCalculatorEvaluate:
    """Tests for the evaluate method."""
    
    def setup_method(self):
        """Set up a fresh calculator for each test."""
        self.calc = Calculator()
    
    def test_evaluate_simple_addition(self):
        """Test evaluating a simple addition expression."""
        result = self.calc.evaluate("2 + 3")
        assert result == 5.0
    
    def test_evaluate_simple_subtraction(self):
        """Test evaluating a simple subtraction expression."""
        result = self.calc.evaluate("10 - 3")
        assert result == 7.0
    
    def test_evaluate_simple_multiplication(self):
        """Test evaluating a simple multiplication expression."""
        result = self.calc.evaluate("4 * 5")
        assert result == 20.0
    
    def test_evaluate_simple_division(self):
        """Test evaluating a simple division expression."""
        result = self.calc.evaluate("100 / 4")
        assert result == 25.0
    
    def test_evaluate_expression_with_parentheses(self):
        """Test evaluating expression with parentheses."""
        result = self.calc.evaluate("(2 + 3) * 4")
        assert result == 20.0
    
    def test_evaluate_complex_expression(self):
        """Test evaluating a complex expression."""
        result = self.calc.evaluate("((2 + 3) * 4) - 1")
        assert result == 19.0
    
    def test_evaluate_expression_with_spaces(self):
        """Test evaluating expression with spaces."""
        result = self.calc.evaluate("  2 + 3  ")
        assert result == 5.0
    
    def test_evaluate_negative_numbers(self):
        """Test evaluating expression with negative numbers."""
        result = self.calc.evaluate("-5 + 3")
        assert result == -2.0
    
    def test_evaluate_decimal_numbers(self):
        """Test evaluating expression with decimal numbers."""
        result = self.calc.evaluate("2.5 + 3.5")
        assert result == 6.0
    
    def test_evaluate_mixed_operations(self):
        """Test evaluating expression with mixed operations."""
        result = self.calc.evaluate("10 + 5 * 2")
        assert result == 20.0  # Multiplication has higher precedence
    
    def test_evaluate_division_by_zero(self):
        """Test that division by zero in expression raises error."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc.evaluate("10 / 0")
        assert "division by zero" in str(exc_info.value).lower()
    
    def test_evaluate_empty_expression(self):
        """Test that empty expression raises error."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc.evaluate("")
        assert "Empty expression" in str(exc_info.value)
    
    def test_evaluate_whitespace_only(self):
        """Test that whitespace-only expression raises error."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc.evaluate("   ")
        assert "Empty expression" in str(exc_info.value)
    
    def test_evaluate_invalid_character(self):
        """Test that invalid characters raise error."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc.evaluate("2 + 3 @ 4")
        assert "Invalid character" in str(exc_info.value)
    
    def test_evaluate_invalid_number(self):
        """Test that invalid numbers raise error."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc.evaluate("2 + abc")
        assert "invalid number" in str(exc_info.value).lower()
    
    def test_evaluate_history_is_updated(self):
        """Test that evaluation updates the history."""
        self.calc.evaluate("2 + 3")
        history = self.calc.get_history()
        assert len(history) == 1
        assert "2 + 3 = 5.0" in history[0]
    
    def test_evaluate_multiple_calculations(self):
        """Test that multiple evaluations build history."""
        self.calc.evaluate("1 + 1")
        self.calc.evaluate("2 + 2")
        self.calc.evaluate("3 + 3")
        history = self.calc.get_history()
        assert len(history) == 3


class TestCalculatorParseNumber:
    """Tests for the _parse_number method."""
    
    def setup_method(self):
        """Set up a fresh calculator for each test."""
        self.calc = Calculator()
    
    def test_parse_integer(self):
        """Test parsing an integer."""
        result = self.calc._parse_number("42")
        assert result == 42.0
    
    def test_parse_negative_integer(self):
        """Test parsing a negative integer."""
        result = self.calc._parse_number("-42")
        assert result == -42.0
    
    def test_parse_float(self):
        """Test parsing a float."""
        result = self.calc._parse_number("3.14")
        assert result == 3.14
    
    def test_parse_negative_float(self):
        """Test parsing a negative float."""
        result = self.calc._parse_number("-3.14")
        assert result == -3.14
    
    def test_parse_invalid_string_raises_error(self):
        """Test that invalid strings raise CalculatorError."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc._parse_number("abc")
        assert "Invalid number" in str(exc_info.value)
    
    def test_parse_empty_string_raises_error(self):
        """Test that empty string raises CalculatorError."""
        with pytest.raises(CalculatorError) as exc_info:
            self.calc._parse_number("")
        assert "Invalid number" in str(exc_info.value)


class TestCalculatorHistory:
    """Tests for the history functionality."""
    
    def setup_method(self):
        """Set up a fresh calculator for each test."""
        self.calc = Calculator()
    
    def test_initial_history_is_empty(self):
        """Test that initial history is empty."""
        history = self.calc.get_history()
        assert history == []
    
    def test_history_returns_copy(self):
        """Test that get_history returns a copy, not the original."""
        self.calc.evaluate("1 + 1")
        history1 = self.calc.get_history()
        history2 = self.calc.get_history()
        assert history1 is not history2
    
    def test_history_format(self):
        """Test that history entries are in correct format."""
        self.calc.evaluate("2 + 2")
        history = self.calc.get_history()
        assert len(history) == 1
        assert "2 + 2" in history[0]
        assert "4" in history[0]


class TestParseArguments:
    """Tests for the parse_arguments function."""
    
    def test_parse_expression_argument(self):
        """Test parsing an expression argument."""
        with patch("sys.argv", ["calculator.py", "2 + 3"]):
            args = parse_arguments()
            assert args.expression == "2 + 3"
    
    def test_parse_empty_expression(self):
        """Test parsing with no expression."""
        with patch("sys.argv", ["calculator.py"]):
            args = parse_arguments()
            assert args.expression == ""
    
    def test_parse_history_flag(self):
        """Test parsing the history flag."""
        with patch("sys.argv", ["calculator.py", "--history"]):
            args = parse_arguments()
            assert args.history is True
    
    def test_parse_both_expression_and_history(self):
        """Test parsing both expression and history flag."""
        with patch("sys.argv", ["calculator.py", "2 + 3", "--history"]):
            args = parse_arguments()
            assert args.expression == "2 + 3"
            assert args.history is True
    
    def test_parse_help_flag(self):
        """Test parsing the help flag."""
        with patch("sys.argv", ["calculator.py", "-h"]):
            with pytest.raises(SystemExit):
                parse_arguments()


class TestMain:
    """Tests for the main function."""
    
    def test_main_success(self):
        """Test main function with a valid expression."""
        with patch("sys.argv", ["calculator.py", "2 + 3"]):
            with patch("sys.stdout", new_callable=lambda: type('obj', (object,), {'write': lambda s, x: None})()):
                result = main()
            assert result == 0
    
    def test_main_division_by_zero(self):
        """Test main function with division by zero."""
        with patch("sys.argv", ["calculator.py", "10 / 0"]):
            with patch("sys.stderr", new_callable=lambda: type('obj', (object,), {'write': lambda s, x: None})()):
                result = main()
            assert result == 1
    
    def test_main_empty_expression(self):
        """Test main function with empty expression."""
        with patch("sys.argv", ["calculator.py"]):
            with patch("sys.stderr", new_callable=lambda: type('obj', (object,), {'write': lambda s, x: None})()):
                result = main()
            assert result == 1
    
    def test_main_invalid_expression(self):
        """Test main function with invalid expression."""
        with patch("sys.argv", ["calculator.py", "2 + @ 3"]):
            with patch("sys.stderr", new_callable=lambda: type('obj', (object,), {'write': lambda s, x: None})()):
                result = main()
            assert result == 1
    
    def test_main_history_flag(self):
        """Test main function with history flag."""
        calc = Calculator()
        calc.evaluate("1 + 1")
        calc.evaluate("2 + 2")
        
        with patch("sys.argv", ["calculator.py", "--history"]):
            with patch("sys.stdout", new_callable=lambda: type('obj', (object,), {'write': lambda s, x: None})()):
                result = main()
            assert result == 0


class TestEdgeCases:
    """Tests for edge cases and special values."""
    
    def setup_method(self):
        """Set up a fresh calculator for each test."""
        self.calc = Calculator()
    
    def test_evaluate_large_numbers(self):
        """Test evaluating very large numbers."""
        result = self.calc.evaluate("1000000000 + 1000000000")
        assert result == 2000000000.0
    
    def test_evaluate_small_numbers(self):
        """Test evaluating very small numbers."""
        result = self.calc.evaluate("0.001 + 0.001")
        assert result == 0.002
    
    def test_evaluate_zero(self):
        """Test evaluating zero."""
        result = self.calc.evaluate("0")
        assert result == 0.0
    
    def test_evaluate_only_positive_sign(self):
        """Test expression with only positive sign."""
        result = self.calc.evaluate("+5")
        assert result == 5.0
    
    def test_evaluate_only_negative_sign(self):
        """Test expression with only negative sign."""
        result = self.calc.evaluate("-5")
        assert result == -5.0
    
    def test_evaluate_multiple_zeros(self):
        """Test expression with multiple zeros."""
        result = self.calc.evaluate("0 + 0 - 0 * 0")
        assert result == 0.0
    
    def test_evaluate_power_of_two(self):
        """Test evaluating power of two."""
        result = self.calc.evaluate("2 ** 10")
        assert result == 1024.0
    
    def test_evaluate_square_root_approximation(self):
        """Test evaluating square root approximation."""
        # sqrt(4) = 2
        result = self.calc.evaluate("4 ** 0.5")
        assert abs(result - 2.0) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

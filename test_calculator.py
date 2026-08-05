#!/usr/bin/env python3
"""
Unit Tests for Calculator Module

Comprehensive test suite for the Calculator class covering:
- Basic arithmetic operations (add, sub, mul, div, pow, mod)
- Mathematical functions (sqrt, abs, log, sin, cos, tan, etc.)
- Statistical functions (min, max, sum, mean, median, std, variance)
- Error handling and edge cases
"""

import unittest
import math
from calculator import Calculator


class TestCalculatorArithmetic(unittest.TestCase):
    """Test basic arithmetic operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_add_positive_numbers(self):
        """Test addition with positive numbers."""
        result = self.calc.add(2, 3)
        self.assertEqual(result, 5)
    
    def test_add_negative_numbers(self):
        """Test addition with negative numbers."""
        result = self.calc.add(-2, -3)
        self.assertEqual(result, -5)
    
    def test_add_mixed_numbers(self):
        """Test addition with mixed positive and negative numbers."""
        result = self.calc.add(-2, 3)
        self.assertEqual(result, 1)
    
    def test_add_floats(self):
        """Test addition with floats."""
        result = self.calc.add(2.5, 3.5)
        self.assertAlmostEqual(result, 6.0)
    
    def test_sub_positive_numbers(self):
        """Test subtraction with positive numbers."""
        result = self.calc.sub(5, 3)
        self.assertEqual(result, 2)
    
    def test_sub_negative_numbers(self):
        """Test subtraction with negative numbers."""
        result = self.calc.sub(-5, -3)
        self.assertEqual(result, -2)
    
    def test_sub_mixed_numbers(self):
        """Test subtraction with mixed positive and negative numbers."""
        result = self.calc.sub(5, -3)
        self.assertEqual(result, 8)
    
    def test_mul_positive_numbers(self):
        """Test multiplication with positive numbers."""
        result = self.calc.mul(2, 3)
        self.assertEqual(result, 6)
    
    def test_mul_negative_numbers(self):
        """Test multiplication with negative numbers."""
        result = self.calc.mul(-2, -3)
        self.assertEqual(result, 6)
    
    def test_mul_mixed_numbers(self):
        """Test multiplication with mixed positive and negative numbers."""
        result = self.calc.mul(-2, 3)
        self.assertEqual(result, -6)
    
    def test_mul_floats(self):
        """Test multiplication with floats."""
        result = self.calc.mul(2.5, 3.5)
        self.assertAlmostEqual(result, 8.75)
    
    def test_div_positive_numbers(self):
        """Test division with positive numbers."""
        result = self.calc.div(10, 2)
        self.assertEqual(result, 5)
    
    def test_div_floats(self):
        """Test division with floats."""
        result = self.calc.div(10, 3)
        self.assertAlmostEqual(result, 3.3333333333333335)
    
    def test_div_by_zero(self):
        """Test division by zero raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.div(10, 0)
        self.assertIn("Division by zero", str(context.exception))
    
    def test_pow_positive_base(self):
        """Test power with positive base."""
        result = self.calc.pow(2, 3)
        self.assertEqual(result, 8)
    
    def test_pow_negative_base(self):
        """Test power with negative base."""
        result = self.calc.pow(-2, 3)
        self.assertEqual(result, -8)
    
    def test_pow_fractional_exponent(self):
        """Test power with fractional exponent."""
        result = self.calc.pow(4, 0.5)
        self.assertAlmostEqual(result, 2.0)
    
    def test_mod_positive_numbers(self):
        """Test modulo with positive numbers."""
        result = self.calc.mod(10, 3)
        self.assertEqual(result, 1)
    
    def test_mod_negative_numbers(self):
        """Test modulo with negative numbers."""
        result = self.calc.mod(-10, 3)
        self.assertEqual(result, -1)
    
    def test_mod_by_zero(self):
        """Test modulo by zero raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.mod(10, 0)
        self.assertIn("Modulo by zero", str(context.exception))


class TestCalculatorMathFunctions(unittest.TestCase):
    """Test mathematical functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_sqrt_positive(self):
        """Test square root with positive number."""
        result = self.calc.sqrt(16)
        self.assertAlmostEqual(result, 4.0)
    
    def test_sqrt_zero(self):
        """Test square root of zero."""
        result = self.calc.sqrt(0)
        self.assertEqual(result, 0.0)
    
    def test_sqrt_negative(self):
        """Test square root of negative number raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.sqrt(-16)
        self.assertIn("negative number", str(context.exception))
    
    def test_abs_positive(self):
        """Test absolute value with positive number."""
        result = self.calc.abs(5)
        self.assertEqual(result, 5)
    
    def test_abs_negative(self):
        """Test absolute value with negative number."""
        result = self.calc.abs(-5)
        self.assertEqual(result, 5)
    
    def test_abs_zero(self):
        """Test absolute value of zero."""
        result = self.calc.abs(0)
        self.assertEqual(result, 0)
    
    def test_log_positive(self):
        """Test logarithm with positive number."""
        result = self.calc.log(100, 10)
        self.assertEqual(result, 2)
    
    def test_log_default_base(self):
        """Test logarithm with default base (10)."""
        result = self.calc.log(100)
        self.assertEqual(result, 2)
    
    def test_log_negative(self):
        """Test logarithm of negative number raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.log(-100)
        self.assertIn("non-positive", str(context.exception))
    
    def test_sin_zero(self):
        """Test sine of zero."""
        result = self.calc.sin(0)
        self.assertAlmostEqual(result, 0.0)
    
    def test_sin_pi_over_2(self):
        """Test sine of pi/2."""
        result = self.calc.sin(math.pi / 2)
        self.assertAlmostEqual(result, 1.0)
    
    def test_cos_zero(self):
        """Test cosine of zero."""
        result = self.calc.cos(0)
        self.assertAlmostEqual(result, 1.0)
    
    def test_tan_zero(self):
        """Test tangent of zero."""
        result = self.calc.tan(0)
        self.assertAlmostEqual(result, 0.0)
    
    def test_tanh_zero(self):
        """Test hyperbolic tangent of zero."""
        result = self.calc.tanh(0)
        self.assertAlmostEqual(result, 0.0)
    
    def test_exp_zero(self):
        """Test exponential of zero."""
        result = self.calc.exp(0)
        self.assertAlmostEqual(result, 1.0)
    
    def test_ln_positive(self):
        """Test natural logarithm with positive number."""
        result = self.calc.ln(math.e)
        self.assertAlmostEqual(result, 1.0)
    
    def test_ln_negative(self):
        """Test natural logarithm of negative number raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.ln(-1)
        self.assertIn("non-positive", str(context.exception))
    
    def test_factorial_positive(self):
        """Test factorial with positive integer."""
        result = self.calc.factorial(5)
        self.assertEqual(result, 120)
    
    def test_factorial_zero(self):
        """Test factorial of zero."""
        result = self.calc.factorial(0)
        self.assertEqual(result, 1)
    
    def test_factorial_negative(self):
        """Test factorial of negative number raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.factorial(-1)
        self.assertIn("negative", str(context.exception))


class TestCalculatorNumberTheory(unittest.TestCase):
    """Test number theory functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_gcd_positive(self):
        """Test greatest common divisor with positive numbers."""
        result = self.calc.gcd(48, 18)
        self.assertEqual(result, 6)
    
    def test_gcd_negative(self):
        """Test greatest common divisor with negative numbers."""
        result = self.calc.gcd(-48, 18)
        self.assertEqual(result, 6)
    
    def test_lcm_positive(self):
        """Test least common multiple with positive numbers."""
        result = self.calc.lcm(4, 6)
        self.assertEqual(result, 12)
    
    def test_lcm_zero(self):
        """Test least common multiple with zero."""
        result = self.calc.lcm(0, 5)
        self.assertEqual(result, 0)


class TestCalculatorStatistics(unittest.TestCase):
    """Test statistical functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_min_single(self):
        """Test minimum with single value."""
        result = self.calc.min(5)
        self.assertEqual(result, 5)
    
    def test_min_multiple(self):
        """Test minimum with multiple values."""
        result = self.calc.min(3, 1, 4, 1, 5, 9, 2, 6)
        self.assertEqual(result, 1)
    
    def test_max_single(self):
        """Test maximum with single value."""
        result = self.calc.max(5)
        self.assertEqual(result, 5)
    
    def test_max_multiple(self):
        """Test maximum with multiple values."""
        result = self.calc.max(3, 1, 4, 1, 5, 9, 2, 6)
        self.assertEqual(result, 9)
    
    def test_sum(self):
        """Test sum."""
        result = self.calc.sum(1, 2, 3, 4, 5)
        self.assertEqual(result, 15)
    
    def test_mean(self):
        """Test mean."""
        result = self.calc.mean(1, 2, 3, 4, 5)
        self.assertAlmostEqual(result, 3.0)
    
    def test_median_odd(self):
        """Test median with odd number of values."""
        result = self.calc.median(1, 3, 2)
        self.assertEqual(result, 2)
    
    def test_median_even(self):
        """Test median with even number of values."""
        result = self.calc.median(1, 3, 2, 4)
        self.assertAlmostEqual(result, 2.5)
    
    def test_std(self):
        """Test standard deviation."""
        result = self.calc.std(1, 2, 3, 4, 5)
        self.assertAlmostEqual(result, 1.5811388300841898)
    
    def test_variance(self):
        """Test variance."""
        result = self.calc.variance(1, 2, 3, 4, 5)
        self.assertAlmostEqual(result, 2.5)
    
    def test_minmax(self):
        """Test minmax."""
        result = self.calc.minmax(3, 1, 4, 1, 5, 9, 2, 6)
        self.assertEqual(result, (1, 9))
    
    def test_minmaxsum(self):
        """Test minmaxsum."""
        result = self.calc.minmaxsum(3, 1, 4, 1, 5, 9, 2, 6)
        self.assertEqual(result, (1, 9, 29))
    
    def test_minmaxmean(self):
        """Test minmaxmean."""
        result = self.calc.minmaxmean(3, 1, 4, 1, 5, 9, 2, 6)
        self.assertAlmostEqual(result, (1, 9, 3.625))
    
    def test_minmaxmeanstd(self):
        """Test minmaxmeanstd."""
        result = self.calc.minmaxmeanstd(3, 1, 4, 1, 5, 9, 2, 6)
        self.assertAlmostEqual(result, (1, 9, 3.625, 2.581988897471611))


class TestCalculatorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_add_with_floats(self):
        """Test addition with floats."""
        result = self.calc.add(0.1, 0.2)
        self.assertAlmostEqual(result, 0.3)
    
    def test_div_with_floats(self):
        """Test division with floats."""
        result = self.calc.div(7, 2)
        self.assertAlmostEqual(result, 3.5)
    
    def test_pow_with_floats(self):
        """Test power with floats."""
        result = self.calc.pow(2.5, 2)
        self.assertAlmostEqual(result, 6.25)
    
    def test_sqrt_with_float(self):
        """Test square root with float."""
        result = self.calc.sqrt(2.25)
        self.assertAlmostEqual(result, 1.5)
    
    def test_log_with_float(self):
        """Test logarithm with float."""
        result = self.calc.log(10.0, 10)
        self.assertEqual(result, 1.0)
    
    def test_factorial_with_large_number(self):
        """Test factorial with large number."""
        result = self.calc.factorial(100)
        self.assertEqual(result, math.factorial(100))
    
    def test_gcd_with_large_numbers(self):
        """Test GCD with large numbers."""
        result = self.calc.gcd(1000000, 500000)
        self.assertEqual(result, 500000)
    
    def test_std_with_two_values(self):
        """Test standard deviation with two values."""
        result = self.calc.std(1, 2)
        self.assertAlmostEqual(result, 0.7071067811865476)
    
    def test_std_with_one_value(self):
        """Test standard deviation with one value."""
        result = self.calc.std(5)
        self.assertEqual(result, 0.0)
    
    def test_variance_with_two_values(self):
        """Test variance with two values."""
        result = self.calc.variance(1, 2)
        self.assertAlmostEqual(result, 0.5)
    
    def test_variance_with_one_value(self):
        """Test variance with one value."""
        result = self.calc.variance(5)
        self.assertEqual(result, 0.0)


class TestCalculatorTypeHandling(unittest.TestCase):
    """Test type handling and conversions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_add_int_and_float(self):
        """Test addition with int and float."""
        result = self.calc.add(2, 3.5)
        self.assertEqual(result, 5.5)
    
    def test_sub_int_and_float(self):
        """Test subtraction with int and float."""
        result = self.calc.sub(5, 2.5)
        self.assertEqual(result, 2.5)
    
    def test_mul_int_and_float(self):
        """Test multiplication with int and float."""
        result = self.calc.mul(2, 3.5)
        self.assertEqual(result, 7.0)
    
    def test_div_int_and_float(self):
        """Test division with int and float."""
        result = self.calc.div(10, 3.0)
        self.assertAlmostEqual(result, 3.3333333333333335)
    
    def test_pow_int_and_float(self):
        """Test power with int and float."""
        result = self.calc.pow(2, 3.0)
        self.assertEqual(result, 8.0)
    
    def test_mod_int_and_float(self):
        """Test modulo with int and float."""
        result = self.calc.mod(10, 3.0)
        self.assertEqual(result, 1.0)


class TestCalculatorIntegration(unittest.TestCase):
    """Integration tests for the calculator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_complex_expression(self):
        """Test complex expression calculation."""
        # (2 + 3) * (4 - 1) = 5 * 3 = 15
        result = self.calc.mul(self.calc.add(2, 3), self.calc.sub(4, 1))
        self.assertEqual(result, 15)
    
    def test_power_chain(self):
        """Test power chain calculation."""
        # 2 ** 3 ** 2 = 2 ** 9 = 512
        result = self.calc.pow(2, self.calc.pow(3, 2))
        self.assertEqual(result, 512)
    
    def test_mod_chain(self):
        """Test modulo chain calculation."""
        # 17 % 3 % 2 = 2 % 2 = 0
        result = self.calc.mod(self.calc.mod(17, 3), 2)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
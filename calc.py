#!/usr/bin/env python3
"""
Simple Calculator in Python
Supports basic arithmetic operations: +, -, *, /, and ** for exponentiation
"""

def add(x, y):
    """Add two numbers"""
    return x + y

def subtract(x, y):
    """Subtract y from x"""
    return x - y

def multiply(x, y):
    """Multiply two numbers"""
    return x * y

def divide(x, y):
    """Divide x by y"""
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y

def power(x, y):
    """Raise x to the power of y"""
    return x ** y

def main():
    """Main function to run the calculator"""
    print("Simple Calculator")
    print("Operations: +, -, *, /, ** (exponentiation)")
    print("Enter 'quit' to exit\n")
    
    while True:
        try:
            # Get user input
            user_input = input("Enter expression (e.g., 5 + 3): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Parse the input
            parts = user_input.split()
            
            if len(parts) != 3:
                print("Invalid format. Use: number operator number (e.g., 5 + 3)")
                continue
            
            try:
                num1 = float(parts[0])
                operator = parts[1]
                num2 = float(parts[2])
            except ValueError:
                print("Invalid numbers. Please enter valid numeric values.")
                continue
            
            # Perform the operation
            if operator == '+':
                result = add(num1, num2)
            elif operator == '-':
                result = subtract(num1, num2)
            elif operator == '*':
                result = multiply(num1, num2)
            elif operator == '/':
                result = divide(num1, num2)
            elif operator == '**':
                result = power(num1, num2)
            else:
                print(f"Unknown operator: {operator}. Use +, -, *, /, or **")
                continue
            
            print(f"Result: {num1} {operator} {num2} = {result}\n")
        
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()

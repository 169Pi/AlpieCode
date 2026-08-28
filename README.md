# Calculator API

A complete calculator application with both command-line interface and REST API using FastAPI.

## Features

### Command-Line Calculator (`calculator.py`)
- Interactive mode with menu-driven interface
- Operations: add, subtract, multiply, divide, power
- Expression evaluation with parentheses support
- Error handling for invalid inputs

### REST API (`main.py`)
- **Endpoints:**
  - `GET /` - API information
  - `GET /health` - Health check
  - `POST /calculate/add` - Add two numbers
  - `POST /calculate/subtract` - Subtract second from first
  - `POST /calculate/multiply` - Multiply two numbers
  - `POST /calculate/divide` - Divide first by second
  - `POST /calculate/power` - Raise base to exponent
  - `POST /calculate/expression` - Evaluate expression string

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command-Line Calculator

Run the interactive calculator:
```bash
python3 calculator.py
```

Example interaction:
```
Enter operation (or 'quit' to exit): add
Enter first number: 5
Enter second number: 3
Result: 8.0
```

### REST API

#### Start the server:
```bash
python3 main.py
```

The API will be available at `http://0.0.0.0:8000`

#### Test with curl:
```bash
# Add numbers
curl -X POST "http://localhost:8000/calculate/add" \
  -H "Content-Type: application/json" \
  -d '{"a": 5, "b": 3}'

# Evaluate expression
curl -X POST "http://localhost:8000/calculate/expression" \
  -H "Content-Type: application/json" \
  -d '{"expression": "2 + 3 * 4"}'
```

#### Test with Python:
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
res = client.post('/calculate/add', json={'a': 5, 'b': 3})
print(res.json())  # {'result': 8.0, 'operation': 'add'}
```

## API Response Format

All calculation endpoints return:
```json
{
  "result": <number>,
  "operation": "<operation_name>"
}
```

Error responses return:
```json
{
  "detail": "<error_message>"
}
```

## Supported Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| add | Addition | 5 + 3 = 8 |
| subtract | Subtraction | 10 - 4 = 6 |
| multiply | Multiplication | 6 * 7 = 42 |
| divide | Division | 15 / 3 = 5 |
| power | Exponentiation | 2^8 = 256 |
| expression | String evaluation | "2 + 3 * 4" = 14 |

## Expression Syntax

The expression evaluator supports:
- Basic arithmetic: `+`, `-`, `*`, `/`
- Exponentiation: `**`
- Parentheses for grouping: `(2 + 3) * 4`
- Decimal numbers: `3.14`

## Error Handling

- **Divide by zero**: Returns 400 error with message "Cannot divide by zero"
- **Invalid expression**: Returns 400 error with syntax error details
- **Missing required fields**: Returns 422 validation error

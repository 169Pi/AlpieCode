"""
FastAPI REST API for Calculator Operations
Provides HTTP endpoints for all calculator functions.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Union
import calculator

app = FastAPI(
    title="Calculator API",
    description="A REST API for performing mathematical calculations",
    version="1.0.0"
)


# Request/Response Models
class OperationRequest(BaseModel):
    """Request model for binary operations."""
    a: float = Field(..., description="First operand")
    b: float = Field(..., description="Second operand")


class PowerRequest(BaseModel):
    """Request model for power operation."""
    base: float = Field(..., description="Base number")
    exponent: float = Field(..., description="Exponent")


class ExpressionRequest(BaseModel):
    """Request model for expression evaluation."""
    expression: str = Field(..., description="Mathematical expression string")


class Result(BaseModel):
    """Response model for calculation results."""
    result: float
    operation: str


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Calculator API",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/calculate/add",
            "/calculate/subtract",
            "/calculate/multiply",
            "/calculate/divide",
            "/calculate/power",
            "/calculate/expression"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Calculator API"}


# Binary operations
@app.post("/calculate/add")
async def add_numbers(request: OperationRequest) -> Result:
    """Add two numbers."""
    result = calculator.add(request.a, request.b)
    return Result(result=result, operation="add")


@app.post("/calculate/subtract")
async def subtract_numbers(request: OperationRequest) -> Result:
    """Subtract second number from first."""
    result = calculator.subtract(request.a, request.b)
    return Result(result=result, operation="subtract")


@app.post("/calculate/multiply")
async def multiply_numbers(request: OperationRequest) -> Result:
    """Multiply two numbers."""
    result = calculator.multiply(request.a, request.b)
    return Result(result=result, operation="multiply")


@app.post("/calculate/divide")
async def divide_numbers(request: OperationRequest) -> Result:
    """Divide first number by second."""
    try:
        result = calculator.divide(request.a, request.b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Result(result=result, operation="divide")


@app.post("/calculate/power")
async def power_numbers(request: PowerRequest) -> Result:
    """Raise base to the power of exponent."""
    result = calculator.power(request.base, request.exponent)
    return Result(result=result, operation="power")


@app.post("/calculate/expression")
async def evaluate_expression(request: ExpressionRequest) -> Result:
    """Evaluate a mathematical expression string."""
    try:
        result = calculator.calculate(request.expression)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Result(result=result, operation="expression")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

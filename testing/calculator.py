"""Calculator module - Example for testing Mirror+Vanisher MCP."""


def add(a, b):
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def subtract(a, b):
    """Subtract b from a.

    Args:
        a: First number
        b: Second number

    Returns:
        Difference of a and b
    """
    return a - b


def multiply(a, b):
    """Multiply two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Product of a and b
    """
    return a * b


def divide(a, b):
    """Divide a by b.

    Args:
        a: Numerator
        b: Denominator

    Returns:
        Quotient of a and b

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# NEW: Power function
def power(a, b):
    return a ** b

# NEW: Square root
def sqrt(a):
    if a < 0:
        raise ValueError("Cannot calculate square root of negative number")
    return a ** 0.5
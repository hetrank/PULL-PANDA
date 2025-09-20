# OLD: Basic error handling
import logging

def process_data(data):
    try:
        result = complex_operation(data)
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def complex_operation(data):
    # Some complex logic
    if not data:
        raise ValueError("Data cannot be empty")
    return data * 2

# NEW: Comprehensive error handling with structured logging
import logging
from typing import Any, Optional
import json
from datetime import datetime

# Setup structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base application error with context"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class ValidationError(AppError):
    """Validation-specific error"""
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)

def process_data(data: Any) -> Any:
    """Process data with comprehensive error handling"""
    try:
        logger.info("Starting data processing", extra={"data_size": len(str(data))})
        result = complex_operation(data)
        logger.info("Data processing completed successfully")
        return result
        
    except ValidationError as e:
        logger.warning("Validation error in data processing", 
                      extra={"error_code": e.code, "details": e.details})
        raise
    except Exception as e:
        logger.error("Unexpected error in data processing", 
                    exc_info=True, 
                    extra={"error_type": type(e).__name__})
        raise AppError("Failed to process data") from e

def complex_operation(data: Any) -> Any:
    """Complex operation with proper validation"""
    if not data:
        raise ValidationError("Data cannot be empty")
    if not isinstance(data, (int, float, list, dict)):
        raise ValidationError("Data must be numeric, list, or dict", "data_type")
    
    # Simulate complex processing
    if isinstance(data, (int, float)):
        return data * 2
    elif isinstance(data, list):
        return [item * 2 for item in data]
    else:  # dict
        return {k: v * 2 for k, v in data.items()}
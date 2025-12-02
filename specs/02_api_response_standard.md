# 02_API_Response_Standard.md

## 📄 Overview

This document defines the standardized JSON response format for the MTF Trading System API Gateway. Adhering to this standard ensures consistency across all API endpoints, improves client-side error handling, and streamlines data consumption. It is implemented using Pydantic models in Python and is designed for seamless integration with the Next.js frontend.

## 📦 Core Response Structures

All API responses are wrapped in one of two generic base models: `APIResponse` for single resource operations or `PaginatedResponse` for list operations.

### `APIResponse<T>`

Used for single resource responses (e.g., fetching a single user, creating a signal).

```python
from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

T = TypeVar('T') # Generic type for data payload

class APIResponse(BaseModel, Generic[T]):
    status: ResponseStatus = Field(..., description="Response status: success, error, or fail")
    data: Optional[T] = Field(None, description="Response payload data")
    message: Optional[str] = Field(None, description="Human-readable message")
    errors: Optional[List[ErrorDetail]] = Field(None, description="List of errors if any")
    meta: Optional[Meta] = Field(None, description="Metadata (pagination, etc.)")
    auth: Optional[AuthTokens] = Field(None, description="Authentication tokens")
    rate_limit: Optional[RateLimitInfo] = Field(None, description="Rate limiting info")
    timestamp: datetime = Field(..., description="Response timestamp")
```

### `PaginatedResponse<T>`

Used for listing multiple resources with pagination metadata.

```python
from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

T = TypeVar('T') # Generic type for data payload

class PaginatedResponse(BaseModel, Generic[T]):
    status: ResponseStatus = Field(..., description="Response status: success, error, or fail")
    data: List[T] = Field(..., description="List of items")
    message: Optional[str] = Field(None, description="Human-readable message")
    meta: Meta = Field(..., description="Pagination metadata")
    rate_limit: Optional[RateLimitInfo] = Field(None, description="Rate limiting info")
    timestamp: datetime = Field(..., description="Response timestamp")
```

## 📊 Enums

### `ResponseStatus`

Indicates the overall status of the API operation.

```python
class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    FAIL = "fail"
```

### `ErrorCode`

Provides specific, machine-readable error codes for client-side handling.

```python
class ErrorCode(str, Enum):
    # Authentication & Authorization (1xxx)
    UNAUTHORIZED = "AUTH_1001"
    FORBIDDEN = "AUTH_1002"
    TOKEN_EXPIRED = "AUTH_1003"
    TOKEN_INVALID = "AUTH_1004"
    INSUFFICIENT_PERMISSIONS = "AUTH_1005"
    
    # Validation Errors (2xxx)
    VALIDATION_ERROR = "VAL_2001"
    REQUIRED_FIELD = "VAL_2002"
    INVALID_FORMAT = "VAL_2003"
    INVALID_EMAIL = "VAL_2004"
    INVALID_PHONE = "VAL_2005"
    INVALID_DATE = "VAL_2006"
    OUT_OF_RANGE = "VAL_2007"
    
    # Resource Errors (3xxx)
    NOT_FOUND = "RES_3001"
    ALREADY_EXISTS = "RES_3002"
    CONFLICT = "RES_3003"
    
    # Business Logic Errors (4xxx)
    INSUFFICIENT_BALANCE = "BIZ_4001"
    OPERATION_NOT_ALLOWED = "BIZ_4002"
    QUOTA_EXCEEDED = "BIZ_4003"
    INVALID_STATE = "BIZ_4004"
    
    # Rate Limiting (5xxx)
    RATE_LIMIT_EXCEEDED = "RATE_5001"
    TOO_MANY_REQUESTS = "RATE_5002"
    
    # Server Errors (9xxx)
    INTERNAL_ERROR = "SRV_9001"
    SERVICE_UNAVAILABLE = "SRV_9002"
    DATABASE_ERROR = "SRV_9003"
    EXTERNAL_SERVICE_ERROR = "SRV_9004"
```

## ✨ Helper Models

### `Meta`

Provides metadata, primarily for pagination.

```python
class Meta(BaseModel):
    page: Optional[int] = Field(None, description="Current page number")
    per_page: Optional[int] = Field(None, description="Items per page")
    total: Optional[int] = Field(None, description="Total items")
    total_pages: Optional[int] = Field(None, description="Total pages")
    
    class Config:
        extra = "allow" # Allows additional custom metadata fields
```

### `AuthTokens`

Contains JWT access and refresh tokens along with their expiry details.

```python
class AuthTokens(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    expires_at: datetime = Field(..., description="Access token expiry timestamp")
```

### `RateLimitInfo`

Provides information about API rate limits for the current client.

```python
class RateLimitInfo(BaseModel):
    limit: int = Field(..., description="Maximum requests allowed")
    remaining: int = Field(..., description="Remaining requests")
    reset: datetime = Field(..., description="When the limit resets")
    reset_in_seconds: int = Field(..., description="Seconds until reset")
```

### `ErrorDetail`

Provides specific details about an error, often associated with a particular field in the request.

```python
class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[ErrorCode] = Field(None, description="Error code for client handling")
```

## 📝 Examples

### 1. Successful Single Resource Response

```json
{
  "status": "success",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "johndoe",
    "email": "john.doe@example.com",
    "is_active": true
  },
  "message": "User retrieved successfully",
  "timestamp": "2025-12-02T10:00:00.000000Z",
  "auth": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "expires_at": "2025-12-02T11:00:00.000000Z"
  }
}
```

### 2. Successful Paginated List Response

```json
{
  "status": "success",
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "symbol": "XAUUSD",
      "direction": "LONG",
      "entry_price": 2000.0,
      "exit_price": 2050.0,
      "pnl_amount": 50.0,
      "pnl_r": 2.5,
      "risk_amount": 20.0,
      "stop_loss_price": 1990.0,
      "take_profit_price": 2060.0,
      "session": "NY",
      "context_score": 7,
      "game_level": "A_GAME",
      "created_at": "2025-12-01T08:00:00.000000Z",
      "updated_at": "2025-12-01T08:00:00.000000Z"
    },
    {
      "id": "f0e9d8c7-b6a5-4321-fedc-ba9876543210",
      "symbol": "EURUSD",
      "direction": "SHORT",
      "entry_price": 1.0800,
      "exit_price": 1.0750,
      "pnl_amount": 50.0,
      "pnl_r": 1.0,
      "risk_amount": 50.0,
      "stop_loss_price": 1.0820,
      "take_profit_price": 1.0700,
      "session": "LONDON",
      "context_score": 9,
      "game_level": "B_GAME",
      "created_at": "2025-11-30T14:30:00.000000Z",
      "updated_at": "2025-11-30T14:30:00.000000Z"
    }
  ],
  "message": "Journal entries retrieved successfully",
  "meta": {
    "page": 1,
    "per_page": 10,
    "total": 50,
    "total_pages": 5
  },
  "timestamp": "2025-12-02T10:05:00.000000Z"
}
```

### 3. Error Response (Validation Error)

```json
{
  "status": "error",
  "data": null,
  "message": "Validation failed for request body",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format",
      "code": "VAL_2003"
    },
    {
      "field": "password",
      "message": "Password must be at least 8 characters long",
      "code": "VAL_2001"
    }
  ],
  "timestamp": "2025-12-02T10:10:00.000000Z"
}
```

### 4. Error Response (General Error)

```json
{
  "status": "error",
  "data": null,
  "message": "Internal Server Error",
  "errors": [
    {
      "message": "An unexpected error occurred on the server.",
      "code": "SRV_9001"
    }
  ],
  "timestamp": "2025-12-02T10:15:00.000000Z"
}
```

## ⚙️ Usage in FastAPI

The `services/api-gateway/app/utils/response.py` module provides helper functions (`success_response`, `error_response`, `paginated_response`) to easily construct these standardized responses within FastAPI routes. Global exception handlers in `app/main.py` ensure that unhandled exceptions and `HTTPException`s are also formatted correctly.

## 💻 Frontend Integration (TypeScript)

The equivalent TypeScript interfaces for these response structures are defined in `frontend/lib/api/types.ts` to ensure type safety and consistency between the backend API and the Next.js frontend application.

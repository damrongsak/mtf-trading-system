from __future__ import annotations

from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Generic type for data payload
T = TypeVar('T')

class ResponseStatus(str, Enum):
    """Standard response status values"""
    SUCCESS = "success"
    ERROR = "error"
    FAIL = "fail"

class ErrorCode(str, Enum):
    """Standard error codes for client-side handling"""
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

class Meta(BaseModel):
    """Metadata for pagination and additional info"""
    page: Optional[int] = Field(None, description="Current page number")
    per_page: Optional[int] = Field(None, description="Items per page")
    total: Optional[int] = Field(None, description="Total items")
    total_pages: Optional[int] = Field(None, description="Total pages")
    
    class Config:
        extra = "allow"  # Allow additional metadata fields

class RateLimitInfo(BaseModel):
    """Rate limiting information"""
    limit: int = Field(..., description="Maximum requests allowed")
    remaining: int = Field(..., description="Remaining requests")
    reset: datetime = Field(..., description="When the limit resets")
    reset_in_seconds: int = Field(..., description="Seconds until reset")

class AuthTokens(BaseModel):
    """Authentication tokens"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    expires_at: datetime = Field(..., description="Access token expiry timestamp")

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[ErrorCode] = Field(None, description="Error code for client handling")

class APIResponse(BaseModel, Generic[T]):
    """Standard API Response Format"""
    status: ResponseStatus = Field(..., description="Response status: success, error, or fail")
    data: Optional[T] = Field(None, description="Response payload data")
    message: Optional[str] = Field(None, description="Human-readable message")
    errors: Optional[List[ErrorDetail]] = Field(None, description="List of errors if any")
    meta: Optional[Meta] = Field(None, description="Metadata (pagination, etc.)")
    auth: Optional[AuthTokens] = Field(None, description="Authentication tokens")
    rate_limit: Optional[RateLimitInfo] = Field(None, description="Rate limiting info")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: List[T] = Field(..., description="List of items")
    message: Optional[str] = None
    meta: Meta = Field(..., description="Pagination metadata")
    rate_limit: Optional[RateLimitInfo] = Field(None, description="Rate limiting info")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

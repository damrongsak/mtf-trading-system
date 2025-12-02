from typing import Any, Optional, List
from datetime import datetime, timedelta
from app.schemas.response import (
    APIResponse, ResponseStatus, Meta, AuthTokens, RateLimitInfo, 
    ErrorCode, ErrorDetail, PaginatedResponse
)

def success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    meta: Optional[Meta] = None,
    auth: Optional[AuthTokens] = None,
    rate_limit: Optional[RateLimitInfo] = None
) -> dict:
    """Create a success response"""
    response = APIResponse(
        status=ResponseStatus.SUCCESS,
        data=data,
        message=message,
        meta=meta,
        auth=auth,
        rate_limit=rate_limit
    )
    return response.model_dump(mode='json', exclude_none=True)

def error_response(
    message: str,
    errors: Optional[List[dict]] = None,
    error_code: Optional[ErrorCode] = None,
    status_code: int = 400
) -> dict:
    """Create an error response"""
    if errors:
        error_details = [ErrorDetail(**e) for e in errors]
    elif error_code:
        error_details = [ErrorDetail(message=message, code=error_code)]
    else:
        error_details = [ErrorDetail(message=message)]
    
    response = APIResponse(
        status=ResponseStatus.ERROR,
        data=None,
        message=message,
        errors=error_details
    )
    return response.model_dump(mode='json', exclude_none=True)

def paginated_response(
    data: List[Any],
    page: int,
    per_page: int,
    total: int,
    message: Optional[str] = None,
    rate_limit: Optional[RateLimitInfo] = None
) -> dict:
    """Create a paginated response"""
    total_pages = (total + per_page - 1) // per_page
    
    response = PaginatedResponse(
        data=data,
        message=message or "Data retrieved successfully",
        meta=Meta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages
        ),
        rate_limit=rate_limit
    )
    return response.model_dump(mode='json', exclude_none=True)

def create_auth_tokens(
    user_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in: int = 3600
) -> AuthTokens:
    """Create authentication tokens"""
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    return AuthTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        expires_at=expires_at
    )

def create_rate_limit_info(
    limit: int,
    remaining: int,
    reset_after_seconds: int
) -> RateLimitInfo:
    """Create rate limit information"""
    reset_time = datetime.utcnow() + timedelta(seconds=reset_after_seconds)
    return RateLimitInfo(
        limit=limit,
        remaining=remaining,
        reset=reset_time,
        reset_in_seconds=reset_after_seconds
    )
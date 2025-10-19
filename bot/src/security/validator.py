"""Security validation for user access and rate limiting."""
import logging
import time
from collections import defaultdict, deque
from typing import Dict

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[int, deque] = defaultdict(deque)
        self.limit = settings.rate_limit_requests
        self.window = settings.rate_limit_window

    def is_allowed(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        now = time.time()
        user_requests = self.requests[user_id]

        # Remove old requests outside the window
        while user_requests and user_requests[0] < now - self.window:
            user_requests.popleft()

        # Check if under limit
        if len(user_requests) < self.limit:
            user_requests.append(now)
            return True

        return False


class SecurityValidator:
    """Validates user access and permissions."""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.allowed_users = settings.allowed_users

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        return user_id in self.allowed_users

    def check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        return self.rate_limiter.is_allowed(user_id)


# Global validator instance
security_validator = SecurityValidator()

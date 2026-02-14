"""
Utility functions for the logging system, including sensitive data sanitization.
"""

import re
import copy
from typing import Any, Dict, List, Pattern, Set


class SanitizationConfig:
    """Configuration for data sanitization rules."""
    
    def __init__(self):
        # Default patterns for sensitive data
        self.api_key_patterns: List[Pattern] = [
            re.compile(r'AIza[0-9A-Za-z\-_]{35}', re.IGNORECASE),  # Google API keys
            re.compile(r'sk-[a-zA-Z0-9]{20,}', re.IGNORECASE),  # OpenAI-style keys
            re.compile(r'[a-zA-Z0-9]{32,}', re.IGNORECASE),  # Generic long tokens
        ]
        
        self.email_pattern: Pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        self.phone_pattern: Pattern = re.compile(
            r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        )
        
        # Field names that should be sanitized
        self.sensitive_field_names: Set[str] = {
            'api_key', 'apikey', 'api-key',
            'secret', 'secret_key', 'secretkey',
            'token', 'access_token', 'auth_token',
            'password', 'passwd', 'pwd',
            'credential', 'credentials',
            'authorization', 'auth',
            'private_key', 'privatekey',
            'session_key', 'sessionkey',
        }
        
        # Field name patterns (suffix/prefix matching)
        self.sensitive_field_patterns: List[Pattern] = [
            re.compile(r'.*_key$', re.IGNORECASE),
            re.compile(r'.*_secret$', re.IGNORECASE),
            re.compile(r'.*_token$', re.IGNORECASE),
            re.compile(r'.*_password$', re.IGNORECASE),
            re.compile(r'.*_credential$', re.IGNORECASE),
        ]
        
        # Partial masking for certain fields (show first/last few chars)
        self.partial_mask_fields: Set[str] = {
            'google_cloud_project',
            'project_id',
            'user_id',
        }
    
    def add_api_key_pattern(self, pattern: str):
        """Add a custom API key pattern."""
        self.api_key_patterns.append(re.compile(pattern, re.IGNORECASE))
    
    def add_sensitive_field(self, field_name: str):
        """Add a custom sensitive field name."""
        self.sensitive_field_names.add(field_name.lower())
    
    def add_sensitive_field_pattern(self, pattern: str):
        """Add a custom sensitive field pattern."""
        self.sensitive_field_patterns.append(re.compile(pattern, re.IGNORECASE))


class DataSanitizer:
    """Sanitizes sensitive data from logs."""
    
    def __init__(self, config: SanitizationConfig = None):
        self.config = config or SanitizationConfig()
        self._mask_string = "***REDACTED***"
        self._partial_mask_char = "*"
    
    def sanitize(self, data: Any) -> Any:
        """
        Sanitize sensitive data from any data structure.
        
        Args:
            data: The data to sanitize (dict, list, str, or primitive)
            
        Returns:
            A deep copy of the data with sensitive information redacted
        """
        if data is None:
            return None
        
        # Make a deep copy to avoid modifying the original
        data_copy = copy.deepcopy(data)
        
        return self._sanitize_recursive(data_copy)
    
    def _sanitize_recursive(self, data: Any) -> Any:
        """Recursively sanitize data structures."""
        if isinstance(data, dict):
            return self._sanitize_dict(data)
        elif isinstance(data, list):
            return self._sanitize_list(data)
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            # Primitive types (int, float, bool, None) pass through
            return data
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a dictionary."""
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if the key should be partially masked
            if key_lower in self.config.partial_mask_fields:
                sanitized[key] = self._partial_mask(str(value))
            # Check if the key itself is sensitive (full redaction)
            elif self._is_sensitive_field(key):
                sanitized[key] = self._mask_string
            else:
                # Recursively sanitize the value
                sanitized[key] = self._sanitize_recursive(value)
        
        return sanitized
    
    def _sanitize_list(self, data: List[Any]) -> List[Any]:
        """Sanitize a list."""
        return [self._sanitize_recursive(item) for item in data]
    
    def _sanitize_string(self, data: str) -> str:
        """Sanitize a string by removing sensitive patterns."""
        sanitized = data
        
        # Sanitize API keys and tokens
        for pattern in self.config.api_key_patterns:
            sanitized = pattern.sub(self._mask_string, sanitized)
        
        # Sanitize email addresses
        sanitized = self.config.email_pattern.sub('[EMAIL_REDACTED]', sanitized)
        
        # Sanitize phone numbers
        sanitized = self.config.phone_pattern.sub('[PHONE_REDACTED]', sanitized)
        
        return sanitized
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name indicates sensitive data."""
        field_lower = field_name.lower()
        
        # Check exact matches
        if field_lower in self.config.sensitive_field_names:
            return True
        
        # Check pattern matches
        for pattern in self.config.sensitive_field_patterns:
            if pattern.match(field_lower):
                return True
        
        return False
    
    def _partial_mask(self, value: str, show_chars: int = 4) -> str:
        """
        Partially mask a string, showing only first and last few characters.
        
        Args:
            value: The string to mask
            show_chars: Number of characters to show at start and end
            
        Returns:
            Partially masked string
        """
        if len(value) <= show_chars * 2:
            # If string is too short, mask completely
            return self._mask_string
        
        start = value[:show_chars]
        end = value[-show_chars:]
        middle_length = len(value) - (show_chars * 2)
        middle = self._partial_mask_char * min(middle_length, 8)  # Cap at 8 asterisks
        
        return f"{start}{middle}{end}"


# Global sanitizer instance with default configuration
_default_sanitizer = DataSanitizer()


def sanitize_data(data: Any, config: SanitizationConfig = None) -> Any:
    """
    Convenience function to sanitize data using default or custom configuration.
    
    Args:
        data: The data to sanitize
        config: Optional custom sanitization configuration
        
    Returns:
        Sanitized copy of the data
    """
    if config:
        sanitizer = DataSanitizer(config)
        return sanitizer.sanitize(data)
    else:
        return _default_sanitizer.sanitize(data)


def create_sanitizer(config: SanitizationConfig = None) -> DataSanitizer:
    """
    Create a new DataSanitizer instance.
    
    Args:
        config: Optional custom sanitization configuration
        
    Returns:
        DataSanitizer instance
    """
    return DataSanitizer(config)

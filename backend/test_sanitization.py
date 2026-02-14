"""
Test script for data sanitization utilities.
"""

from logging_system.utils import sanitize_data, DataSanitizer, SanitizationConfig


def test_api_key_sanitization():
    """Test that API keys are properly sanitized."""
    print("\n=== Testing API Key Sanitization ===")
    
    data = {
        "api_key": "AIzaSyDXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "google_api_key": "AIzaSyDYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",
        "secret_token": "sk-1234567890abcdefghij",
        "normal_field": "this should not be sanitized"
    }
    
    sanitized = sanitize_data(data)
    
    print(f"Original api_key: {data['api_key']}")
    print(f"Sanitized api_key: {sanitized['api_key']}")
    print(f"Original google_api_key: {data['google_api_key']}")
    print(f"Sanitized google_api_key: {sanitized['google_api_key']}")
    print(f"Original secret_token: {data['secret_token']}")
    print(f"Sanitized secret_token: {sanitized['secret_token']}")
    print(f"Normal field: {sanitized['normal_field']}")
    
    assert sanitized['api_key'] == "***REDACTED***"
    assert sanitized['google_api_key'] == "***REDACTED***"
    assert sanitized['secret_token'] == "***REDACTED***"
    assert sanitized['normal_field'] == "this should not be sanitized"
    print("✓ API key sanitization passed")


def test_email_sanitization():
    """Test that email addresses are sanitized in strings."""
    print("\n=== Testing Email Sanitization ===")
    
    data = {
        "message": "Contact us at support@example.com for help",
        "user_info": "User john.doe@company.org submitted a request"
    }
    
    sanitized = sanitize_data(data)
    
    print(f"Original message: {data['message']}")
    print(f"Sanitized message: {sanitized['message']}")
    print(f"Original user_info: {data['user_info']}")
    print(f"Sanitized user_info: {sanitized['user_info']}")
    
    assert "support@example.com" not in sanitized['message']
    assert "[EMAIL_REDACTED]" in sanitized['message']
    assert "john.doe@company.org" not in sanitized['user_info']
    assert "[EMAIL_REDACTED]" in sanitized['user_info']
    print("✓ Email sanitization passed")


def test_phone_sanitization():
    """Test that phone numbers are sanitized in strings."""
    print("\n=== Testing Phone Number Sanitization ===")
    
    data = {
        "contact": "Call us at 555-123-4567",
        "info": "Phone: (555) 987-6543 or +1-555-111-2222"
    }
    
    sanitized = sanitize_data(data)
    
    print(f"Original contact: {data['contact']}")
    print(f"Sanitized contact: {sanitized['contact']}")
    print(f"Original info: {data['info']}")
    print(f"Sanitized info: {sanitized['info']}")
    
    assert "555-123-4567" not in sanitized['contact']
    assert "[PHONE_REDACTED]" in sanitized['contact']
    assert "(555) 987-6543" not in sanitized['info']
    assert "[PHONE_REDACTED]" in sanitized['info']
    print("✓ Phone number sanitization passed")


def test_nested_structure_sanitization():
    """Test sanitization of nested data structures."""
    print("\n=== Testing Nested Structure Sanitization ===")
    
    data = {
        "user": {
            "name": "John Doe",
            "email": "john@example.com",
            "api_key": "secret123"
        },
        "requests": [
            {
                "id": 1,
                "auth_token": "token_abc123",
                "data": "normal data"
            },
            {
                "id": 2,
                "password": "mypassword",
                "data": "more data"
            }
        ]
    }
    
    sanitized = sanitize_data(data)
    
    print(f"Original user api_key: {data['user']['api_key']}")
    print(f"Sanitized user api_key: {sanitized['user']['api_key']}")
    print(f"Original request auth_token: {data['requests'][0]['auth_token']}")
    print(f"Sanitized request auth_token: {sanitized['requests'][0]['auth_token']}")
    print(f"Original request password: {data['requests'][1]['password']}")
    print(f"Sanitized request password: {sanitized['requests'][1]['password']}")
    
    assert sanitized['user']['api_key'] == "***REDACTED***"
    assert sanitized['user']['name'] == "John Doe"
    assert sanitized['requests'][0]['auth_token'] == "***REDACTED***"
    assert sanitized['requests'][0]['data'] == "normal data"
    assert sanitized['requests'][1]['password'] == "***REDACTED***"
    print("✓ Nested structure sanitization passed")


def test_partial_masking():
    """Test partial masking for certain fields."""
    print("\n=== Testing Partial Masking ===")
    
    data = {
        "google_cloud_project": "my-project-id-12345",
        "project_id": "another-project-67890",
        "api_key": "should_be_fully_redacted"
    }
    
    sanitized = sanitize_data(data)
    
    print(f"Original google_cloud_project: {data['google_cloud_project']}")
    print(f"Sanitized google_cloud_project: {sanitized['google_cloud_project']}")
    print(f"Original project_id: {data['project_id']}")
    print(f"Sanitized project_id: {sanitized['project_id']}")
    print(f"Original api_key: {data['api_key']}")
    print(f"Sanitized api_key: {sanitized['api_key']}")
    
    # Partial mask should show first and last 4 chars
    assert sanitized['google_cloud_project'].startswith("my-p")
    assert sanitized['google_cloud_project'].endswith("2345")
    assert "*" in sanitized['google_cloud_project']
    
    assert sanitized['project_id'].startswith("anot")
    assert sanitized['project_id'].endswith("7890")
    
    # api_key should be fully redacted
    assert sanitized['api_key'] == "***REDACTED***"
    print("✓ Partial masking passed")


def test_custom_sanitization_config():
    """Test custom sanitization configuration."""
    print("\n=== Testing Custom Sanitization Config ===")
    
    # Create custom config
    config = SanitizationConfig()
    config.add_sensitive_field("custom_secret")
    config.add_api_key_pattern(r'CUSTOM-[A-Z0-9]{10}')
    
    data = {
        "custom_secret": "this should be redacted",
        "message": "Token: CUSTOM-ABC1234567",
        "normal_field": "this is fine"
    }
    
    sanitizer = DataSanitizer(config)
    sanitized = sanitizer.sanitize(data)
    
    print(f"Original custom_secret: {data['custom_secret']}")
    print(f"Sanitized custom_secret: {sanitized['custom_secret']}")
    print(f"Original message: {data['message']}")
    print(f"Sanitized message: {sanitized['message']}")
    
    assert sanitized['custom_secret'] == "***REDACTED***"
    assert "CUSTOM-ABC1234567" not in sanitized['message']
    assert sanitized['normal_field'] == "this is fine"
    print("✓ Custom sanitization config passed")


def test_original_data_unchanged():
    """Test that original data is not modified."""
    print("\n=== Testing Original Data Unchanged ===")
    
    original_data = {
        "api_key": "secret123",
        "nested": {
            "password": "mypassword"
        }
    }
    
    # Create a reference to check
    original_api_key = original_data['api_key']
    original_password = original_data['nested']['password']
    
    # Sanitize
    sanitized = sanitize_data(original_data)
    
    # Check original is unchanged
    print(f"Original api_key after sanitization: {original_data['api_key']}")
    print(f"Original password after sanitization: {original_data['nested']['password']}")
    print(f"Sanitized api_key: {sanitized['api_key']}")
    print(f"Sanitized password: {sanitized['nested']['password']}")
    
    assert original_data['api_key'] == original_api_key
    assert original_data['nested']['password'] == original_password
    assert sanitized['api_key'] == "***REDACTED***"
    assert sanitized['nested']['password'] == "***REDACTED***"
    print("✓ Original data unchanged passed")


if __name__ == "__main__":
    print("Running sanitization tests...")
    
    try:
        test_api_key_sanitization()
        test_email_sanitization()
        test_phone_sanitization()
        test_nested_structure_sanitization()
        test_partial_masking()
        test_custom_sanitization_config()
        test_original_data_unchanged()
        
        print("\n" + "="*50)
        print("✓ All sanitization tests passed!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise

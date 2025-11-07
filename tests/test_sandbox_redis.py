import pytest
import redis
import os
import yaml


def load_redis_password():
    """Load Redis password from secrets.yaml or environment variable"""
    # Try environment variable first
    password = os.getenv("REDIS_PASSWORD")
    if password:
        return password
    
    # Try loading from secrets.yaml
    secrets_path = os.path.join(os.path.dirname(__file__), '..', 'secrets.yaml')
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path) as f:
                secrets = yaml.safe_load(f)
                password = secrets.get('redis', {}).get('password')
                if password:
                    return password
        except (yaml.YAMLError, IOError, KeyError):
            pass
    
    # No password found - this is a critical error
    raise ValueError(
        "REDIS_PASSWORD is required! Set it as an environment variable or in secrets.yaml. "
        "See docs/SECRETS.md for setup instructions."
    )


REDIS_PASSWORD = load_redis_password()


def is_container_running():
    """Check if the Redis container is running and accessible."""
    try:
        client = redis.Redis(host='localhost', port=16379, password=REDIS_PASSWORD, socket_connect_timeout=2)
        client.ping()
        return True
    except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
        return False


@pytest.fixture(scope="module")
def redis_client():
    """Fixture to provide Redis client if container is running."""
    if not is_container_running():
        pytest.skip("Sandbox container is not running")
    
    client = redis.Redis(host='localhost', port=16379, password=REDIS_PASSWORD, decode_responses=True)
    yield client
    client.close()


class TestSandboxRedis:
    """Test Redis operations in the sandbox container."""
    
    def test_redis_connection(self, redis_client):
        """Test that we can connect to Redis."""
        assert redis_client.ping() is True
    
    def test_redis_set_get(self, redis_client):
        """Test setting and getting a value in Redis."""
        key = "test:sandbox:key"
        value = "test_value"
        
        # Set a value
        result = redis_client.set(key, value)
        assert result is True
        
        # Get the value back
        retrieved_value = redis_client.get(key)
        assert retrieved_value == value
        
        # Clean up
        redis_client.delete(key)
    
    def test_redis_set_with_expiry(self, redis_client):
        """Test setting a value with expiration."""
        key = "test:sandbox:expiry"
        value = "expiring_value"
        
        # Set with 10 second expiry
        result = redis_client.setex(key, 10, value)
        assert result is True
        
        # Value should exist
        assert redis_client.get(key) == value
        
        # Check TTL
        ttl = redis_client.ttl(key)
        assert 0 < ttl <= 10
        
        # Clean up
        redis_client.delete(key)
    
    def test_redis_delete(self, redis_client):
        """Test deleting a key from Redis."""
        key = "test:sandbox:delete"
        value = "to_be_deleted"
        
        # Set a value
        redis_client.set(key, value)
        assert redis_client.get(key) == value
        
        # Delete the key
        result = redis_client.delete(key)
        assert result == 1
        
        # Key should not exist
        assert redis_client.get(key) is None
    
    def test_redis_multiple_keys(self, redis_client):
        """Test setting and getting multiple keys."""
        keys_values = {
            "test:sandbox:key1": "value1",
            "test:sandbox:key2": "value2",
            "test:sandbox:key3": "value3"
        }
        
        # Set multiple keys
        for key, value in keys_values.items():
            redis_client.set(key, value)
        
        # Get all keys
        for key, expected_value in keys_values.items():
            actual_value = redis_client.get(key)
            assert actual_value == expected_value
        
        # Clean up
        redis_client.delete(*keys_values.keys())
    
    def test_redis_exists(self, redis_client):
        """Test checking if a key exists."""
        key = "test:sandbox:exists"
        
        # Key should not exist initially
        assert redis_client.exists(key) == 0
        
        # Set a value
        redis_client.set(key, "exists_value")
        
        # Key should exist now
        assert redis_client.exists(key) == 1
        
        # Clean up
        redis_client.delete(key)

"""
Redis connection helper with connection pooling and error handling.
"""

import logging
import redis
import yaml
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Global connection pool (singleton pattern)
_redis_pool = None
_redis_client = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get a Redis client using connection pooling.
    
    Returns:
        Redis client or None if connection fails
    """
    global _redis_pool, _redis_client
    
    if _redis_client is not None:
        try:
            # Test if connection is still alive
            _redis_client.ping()
            return _redis_client
        except Exception:
            # Connection lost, recreate
            _redis_client = None
            _redis_pool = None
    
    try:
        # Load configuration with error handling
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        secrets_path = Path(__file__).parent.parent.parent / "secrets.yaml"
        
        redis_host = 'localhost'
        redis_port = 6379
        redis_password = None
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'redis' in config:
                        redis_host = config['redis'].get('host', redis_host)
                        redis_port = config['redis'].get('port', redis_port)
            except (yaml.YAMLError, IOError) as e:
                logger.warning(f"Error loading config.yaml: {e}, using defaults")
        
        if secrets_path.exists():
            try:
                with open(secrets_path, 'r') as f:
                    secrets = yaml.safe_load(f)
                    if secrets and 'redis' in secrets:
                        redis_password = secrets['redis'].get('password')
            except (yaml.YAMLError, IOError) as e:
                logger.warning(f"Error loading secrets.yaml: {e}, using no password")
        
        # Create connection pool if not exists
        if _redis_pool is None:
            _redis_pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=0,
                password=redis_password,
                decode_responses=True,
                max_connections=10
            )
        
        # Create client from pool
        _redis_client = redis.Redis(connection_pool=_redis_pool)
        
        # Test connection
        _redis_client.ping()
        
        return _redis_client
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

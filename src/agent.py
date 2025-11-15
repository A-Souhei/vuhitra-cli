import yaml, requests
import time
import logging
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception
from src.utils.token_limit_manager import get_token_limit_manager

logger = logging.getLogger(__name__)


def generate(model, prompt):
    """Generate response from LLM with automatic token limit discovery.

    Args:
        model: Model name
        prompt: User prompt

    Returns:
        Tuple of (response_text, execution_time_ms)
    """
    url = None  # Initialize for error handling

    try:
        config = ConfigLoader()
        protocol = config.get_ollama_protocol()
        host = config.get_ollama_host()
        port = config.get_ollama_port()
        api_path = config.get_ollama_api_path()
        url = f'{protocol}://{host}:{port}{api_path}'

        start_time = time.time()
        r = requests.post(url, json={'model': model, 'prompt': prompt, 'stream': False}, timeout=30)
        execution_time_ms = int((time.time() - start_time) * 1000)

        r.raise_for_status()
        response_text = r.json().get('response', 'ERROR: No response field in JSON')

        return response_text, execution_time_ms

    except requests.exceptions.HTTPError as e:
        # Check if this is a token limit error (HTTP 400)
        if e.response.status_code == 400:
            try:
                error_data = e.response.json()
                error_message = error_data.get('error', str(e))
            except Exception:
                error_message = str(e)

            # Check if error is related to token/context limits
            error_lower = error_message.lower()
            is_token_error = any(keyword in error_lower for keyword in [
                'context', 'length', 'token', 'maximum', 'exceeded', 'too long'
            ])

            if is_token_error:
                # Try to extract and store the token limit
                token_manager = get_token_limit_manager()
                discovered_limit = token_manager.extract_limit_from_error(error_message)

                if discovered_limit:
                    token_manager.store_limit(model, discovered_limit)
                    logger.warning(f"Discovered token limit for {model}: {discovered_limit}")

                    return (
                        f"ERROR: Token limit exceeded for {model} (limit: {discovered_limit} tokens)\n"
                        f"This limit has been saved for future reference.\n"
                        f"Suggestion: Use /clear context to free up space or shorten your prompt."
                    ), 0
                else:
                    # Token error but couldn't extract limit
                    return (
                        f"ERROR: Token/context limit exceeded for {model}\n"
                        f"Error: {error_message}\n"
                        f"Suggestion: Use /clear context to free up space or shorten your prompt."
                    ), 0

        # Other HTTP errors
        handle_exception(e, context={
            'function': 'generate',
            'model': model,
            'url': url,
            'status_code': e.response.status_code,
            'error_type': 'HTTPError'
        })
        return f'ERROR: HTTP {e.response.status_code} - {str(e)}', 0

    except requests.exceptions.RequestException as e:
        handle_exception(e, context={
            'function': 'generate',
            'model': model,
            'url': url if url else 'N/A',
            'error_type': 'RequestException'
        })
        return f'ERROR: {str(e)}', 0

    except Exception as e:
        handle_exception(e, context={
            'function': 'generate',
            'model': model,
            'error_type': 'GeneralException'
        })
        return f'ERROR: {str(e)}', 0

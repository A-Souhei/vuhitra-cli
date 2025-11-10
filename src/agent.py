import yaml, requests
import time
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception

def generate(model, prompt):
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
    except requests.exceptions.RequestException as e:
        handle_exception(e, context={
            'function': 'generate',
            'model': model,
            'url': url if 'url' in locals() else 'N/A',
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

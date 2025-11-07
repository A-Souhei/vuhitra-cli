import yaml, requests

def load_host():
    with open('config.yaml') as f:
        return yaml.safe_load(f)['host']

def generate(model, prompt):
    url = f'http://{load_host()}:11434/api/generate'
    r = requests.post(url, json={'model': model, 'prompt': prompt, 'stream': False})
    return r.json().get('response', 'ERROR')

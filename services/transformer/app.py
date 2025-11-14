"""
Transformer NLP Service

A Flask-based microservice that provides transformer-based NLP capabilities:
- Code recognition and separation
- Context compaction
- Keyword extraction
- Text reformulation and typo fixing
- Matrix context generation for LLM consumption
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.code_recognizer import CodeRecognizer
from src.context_compacter import ContextCompacter


# Initialize Sentry (optional)
sentry_dsn = os.getenv('SENTRY_DSN', '')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
        environment=os.getenv('ENVIRONMENT', 'DEV')
    )

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize services (lazy loading)
code_recognizer = None
context_compacter = None


def get_code_recognizer():
    """Get or initialize code recognizer (lazy loading)."""
    global code_recognizer
    if code_recognizer is None:
        print("Initializing Code Recognizer...")
        code_recognizer = CodeRecognizer()
    return code_recognizer


def get_context_compacter():
    """Get or initialize context compacter (lazy loading)."""
    global context_compacter
    if context_compacter is None:
        print("Initializing Context Compacter (loading models)...")
        context_compacter = ContextCompacter()
        print("Context Compacter initialized successfully")
    return context_compacter


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'transformer-nlp',
        'version': '1.0.0'
    })


@app.route('/api/recognize-code', methods=['POST'])
def recognize_code():
    """
    Recognize and separate code from text.

    Request body:
    {
        "text": "string - the text to analyze"
    }

    Response:
    {
        "code_blocks": [...],
        "text_segments": [...],
        "has_code": boolean
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400

        text = data['text']
        recognizer = get_code_recognizer()

        # Separate code and text
        code_blocks, text_segments = recognizer.separate_code_and_text(text)

        return jsonify({
            'code_blocks': code_blocks,
            'text_segments': text_segments,
            'has_code': len(code_blocks) > 0,
            'code_block_count': len(code_blocks),
            'text_segment_count': len(text_segments)
        })

    except Exception as e:
        print(f"Error in recognize_code: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract-keywords', methods=['POST'])
def extract_keywords():
    """
    Extract keywords from text.

    Request body:
    {
        "text": "string - the text to analyze",
        "top_n": number (optional) - number of keywords to extract
    }

    Response:
    {
        "keywords": [{"keyword": "...", "score": 0.95}, ...]
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400

        text = data['text']
        top_n = data.get('top_n', 10)

        compacter = get_context_compacter()
        keywords = compacter.extract_keywords(text, top_n=top_n)

        return jsonify({
            'keywords': keywords,
            'count': len(keywords)
        })

    except Exception as e:
        print(f"Error in extract_keywords: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/compact-text', methods=['POST'])
def compact_text():
    """
    Compact text by removing redundancy and extracting key information.

    Request body:
    {
        "text": "string - the text to compact",
        "max_sentences": number (optional) - maximum sentences to keep
    }

    Response:
    {
        "original_text": "...",
        "compacted_text": "...",
        "keywords": [...],
        "compression_ratio": 0.65,
        "sentence_count_before": 10,
        "sentence_count_after": 6
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400

        text = data['text']
        max_sentences = data.get('max_sentences', None)

        compacter = get_context_compacter()
        result = compacter.compact_text(text, max_sentences=max_sentences)

        return jsonify(result)

    except Exception as e:
        print(f"Error in compact_text: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/compact-prompt', methods=['POST'])
def compact_prompt():
    """
    Compact a user prompt if it's too verbose.

    Request body:
    {
        "prompt": "string - the user's prompt"
    }

    Response:
    {
        "original_prompt": "...",
        "compacted_prompt": "...",
        "was_compacted": boolean,
        "keywords": [...]
    }
    """
    try:
        data = request.get_json()

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing required field: prompt'}), 400

        prompt = data['prompt']

        compacter = get_context_compacter()
        result = compacter.compact_prompt(prompt)

        return jsonify(result)

    except Exception as e:
        print(f"Error in compact_prompt: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/compact-heuristics', methods=['POST'])
def compact_heuristics():
    """
    Compact heuristics from the sandbox service.

    Request body:
    {
        "heuristics": "string - the heuristics text"
    }

    Response:
    {
        "original_heuristics": "...",
        "compacted_heuristics": "...",
        "keywords": [...]
    }
    """
    try:
        data = request.get_json()

        if not data or 'heuristics' not in data:
            return jsonify({'error': 'Missing required field: heuristics'}), 400

        heuristics = data['heuristics']

        compacter = get_context_compacter()
        result = compacter.compact_heuristics(heuristics)

        return jsonify(result)

    except Exception as e:
        print(f"Error in compact_heuristics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/create-matrix-context', methods=['POST'])
def create_matrix_context():
    """
    Create a matrix-style context for LLM consumption.

    This is the main endpoint that combines all features:
    - Separates code from text
    - Compacts text components
    - Preserves code blocks
    - Generates structured matrix output

    Request body:
    {
        "prompt": "string - user's prompt",
        "heuristics": "string (optional) - heuristics from sandbox",
        "context": "string (optional) - additional context",
        "raw_text": "string (optional) - text that may contain code"
    }

    Response:
    {
        "prompt": {
            "original": "...",
            "compacted": "...",
            "keywords": [...]
        },
        "heuristics": {
            "original": "...",
            "compacted": "...",
            "keywords": [...]
        },
        "context": {
            "original": "...",
            "compacted": "...",
            "keywords": [...]
        },
        "code_blocks": [...],
        "formatted_for_llm": "string - ready-to-use formatted context"
    }
    """
    try:
        data = request.get_json()

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing required field: prompt'}), 400

        prompt = data['prompt']
        heuristics = data.get('heuristics', '')
        context = data.get('context', '')
        raw_text = data.get('raw_text', '')

        # Step 1: Recognize and extract code from any raw text
        code_blocks = []
        if raw_text:
            recognizer = get_code_recognizer()
            extracted_code, text_segments = recognizer.separate_code_and_text(raw_text)
            code_blocks.extend(extracted_code)

            # Add text segments to context
            if text_segments:
                additional_text = ' '.join([seg['content'] for seg in text_segments])
                context = f"{context}\n{additional_text}" if context else additional_text

        # Step 2: Create matrix context
        compacter = get_context_compacter()
        matrix = compacter.create_matrix_context(
            prompt=prompt,
            heuristics=heuristics,
            context=context,
            code_blocks=code_blocks
        )

        return jsonify(matrix)

    except Exception as e:
        print(f"Error in create_matrix_context: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/fix-typos', methods=['POST'])
def fix_typos():
    """
    Fix typos and grammar issues in text.

    Request body:
    {
        "text": "string - the text to fix"
    }

    Response:
    {
        "original_text": "...",
        "fixed_text": "..."
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400

        text = data['text']

        compacter = get_context_compacter()
        fixed_text = compacter.fix_typos_and_grammar(text)

        return jsonify({
            'original_text': text,
            'fixed_text': fixed_text
        })

    except Exception as e:
        print(f"Error in fix_typos: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.getenv('PORT', 5050))

    print(f"Starting Transformer NLP Service on port {port}...")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /api/recognize-code - Recognize and separate code from text")
    print("  POST /api/extract-keywords - Extract keywords from text")
    print("  POST /api/compact-text - Compact text by removing redundancy")
    print("  POST /api/compact-prompt - Compact verbose prompts")
    print("  POST /api/compact-heuristics - Compact heuristics text")
    print("  POST /api/create-matrix-context - Create matrix-style context (MAIN)")
    print("  POST /api/fix-typos - Fix typos and grammar")
    print()

    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )

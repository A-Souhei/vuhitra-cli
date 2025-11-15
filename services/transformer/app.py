"""
Transformer NLP Service

A Flask-based microservice that provides transformer-based NLP capabilities:
- Code recognition and separation
- Context compaction
- Keyword extraction
- Text reformulation and typo fixing
- Matrix context generation for LLM consumption
- Embedding generation for semantic search
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.code_recognizer import CodeRecognizer
from src.context_compacter import ContextCompacter
from src.sentiment_analyzer import SentimentAnalyzer
from src.errors_handler.error_handler import get_error_handler

# Initialize error handler
error_handler = get_error_handler()

# Configure error handler with environment variables
sentry_dsn = os.getenv('SENTRY_DSN', '')
environment = os.getenv('ENVIRONMENT', 'DEV')

error_handler.configure(
    sentry_dsn=sentry_dsn if sentry_dsn else None,
    mode=environment,
    enable_logging=environment == 'DEV'
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Input validation constants
MAX_TEXT_LENGTH = 100000  # 100KB of text
MIN_TEXT_LENGTH = 1

# Initialize services (lazy loading)
code_recognizer = None
context_compacter = None
sentiment_analyzer = None

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


def get_sentiment_analyzer():
    """Get or initialize sentiment analyzer (lazy loading)."""
    global sentiment_analyzer
    if sentiment_analyzer is None:
        print("Initializing Sentiment Analyzer (loading transformer model)...")
        sentiment_analyzer = SentimentAnalyzer()
        print("Sentiment Analyzer initialized successfully")
    return sentiment_analyzer


def validate_text_input(text: str, field_name: str = "text") -> tuple:
    """
    Validate text input for size and emptiness.

    Args:
        text: The text to validate
        field_name: Name of the field (for error messages)

    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    if not text or not isinstance(text, str):
        return False, f"Field '{field_name}' must be a non-empty string"

    text_stripped = text.strip()
    if len(text_stripped) < MIN_TEXT_LENGTH:
        return False, f"Field '{field_name}' is empty or too short"

    if len(text) > MAX_TEXT_LENGTH:
        return False, f"Field '{field_name}' exceeds maximum length of {MAX_TEXT_LENGTH} characters"

    return True, None


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

        # Validate input
        is_valid, error_msg = validate_text_input(text, 'text')
        if not is_valid:
            return jsonify({'error': error_msg}), 400

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
        error_handler.handle_exception(
            e,
            context={
                "endpoint": "/api/recognize-code",
                "has_data": request.data is not None
            }
        )
        return jsonify({'error': 'Internal server error'}), 500


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

        # Validate input
        is_valid, error_msg = validate_text_input(text, 'text')
        if not is_valid:
            return jsonify({'error': error_msg}), 400

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

        # Validate input
        is_valid, error_msg = validate_text_input(text, 'text')
        if not is_valid:
            return jsonify({'error': error_msg}), 400

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
        "prompt": "string - the user's prompt",
        "threshold": number (optional) - character count threshold (default: 500)
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

        # Validate input
        is_valid, error_msg = validate_text_input(prompt, 'prompt')
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        threshold = data.get('threshold', 500)

        compacter = get_context_compacter()
        result = compacter.compact_prompt(prompt, threshold=threshold)

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

        # Validate input (allow empty heuristics as it's optional context)
        if heuristics and isinstance(heuristics, str):
            is_valid, error_msg = validate_text_input(heuristics, 'heuristics')
            if not is_valid:
                return jsonify({'error': error_msg}), 400

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

        # Validate prompt (required)
        is_valid, error_msg = validate_text_input(prompt, 'prompt')
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        heuristics = data.get('heuristics', '')
        context = data.get('context', '')
        raw_text = data.get('raw_text', '')

        # Validate optional fields if provided
        if heuristics:
            is_valid, error_msg = validate_text_input(heuristics, 'heuristics')
            if not is_valid:
                return jsonify({'error': error_msg}), 400

        if context:
            is_valid, error_msg = validate_text_input(context, 'context')
            if not is_valid:
                return jsonify({'error': error_msg}), 400

        if raw_text:
            is_valid, error_msg = validate_text_input(raw_text, 'raw_text')
            if not is_valid:
                return jsonify({'error': error_msg}), 400

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


@app.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment():
    """
    Analyze sentiment using transformer model.

    Request body:
    {
        "text": "string - the text to analyze",
        "texts": ["list (optional) - multiple texts for batch analysis"]
    }

    Response (single text):
    {
        "label": "POSITIVE" or "NEGATIVE",
        "score": 0.95,
        "compound": 0.95  # VADER-compatible score (-1 to 1)
    }

    Response (batch):
    {
        "results": [
            {"label": "POSITIVE", "score": 0.95, "compound": 0.95},
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Check for batch or single text
        if 'texts' in data:
            # Batch analysis
            texts = data['texts']
            if not isinstance(texts, list):
                return jsonify({'error': 'Field "texts" must be a list'}), 400

            if len(texts) == 0:
                return jsonify({'error': 'Field "texts" cannot be empty'}), 400

            # Validate each text in the batch
            for i, text in enumerate(texts):
                is_valid, error_msg = validate_text_input(text, f'texts[{i}]')
                if not is_valid:
                    return jsonify({'error': error_msg}), 400

            analyzer = get_sentiment_analyzer()
            results = analyzer.analyze_batch(texts)

            return jsonify({'results': results})

        elif 'text' in data:
            # Single text analysis
            text = data['text']

            # Validate input
            is_valid, error_msg = validate_text_input(text, 'text')
            if not is_valid:
                return jsonify({'error': error_msg}), 400

            analyzer = get_sentiment_analyzer()
            result = analyzer.analyze(text)

            return jsonify(result)

        else:
            return jsonify({'error': 'Missing required field: text or texts'}), 400

    except Exception as e:
        print(f"Error in analyze_sentiment: {e}")
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

        # Validate input
        is_valid, error_msg = validate_text_input(text, 'text')
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        compacter = get_context_compacter()
        fixed_text = compacter.fix_typos_and_grammar(text)

        return jsonify({
            'original_text': text,
            'fixed_text': fixed_text
        })

    except Exception as e:
        print(f"Error in fix_typos: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-embedding', methods=['POST'])
def generate_embedding():
    """
    Generate embeddings for text using sentence-transformers.

    Request body:
    {
        "text": "string - the text to generate embeddings for",
        "texts": ["list", "of", "texts"] (optional) - multiple texts for batch processing
    }

    Response:
    {
        "embedding": [0.123, -0.456, ...],  # For single text
        "embeddings": [[...], [...], ...],  # For batch processing
        "dimension": 384,
        "model": "all-MiniLM-L6-v2"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        # Support both single text and batch processing
        texts = None
        if 'texts' in data and isinstance(data['texts'], list):
            texts = data['texts']
            if not texts:
                return jsonify({'error': 'texts list cannot be empty'}), 400
            # Validate each text
            for idx, text in enumerate(texts):
                is_valid, error_msg = validate_text_input(text, f'texts[{idx}]')
                if not is_valid:
                    return jsonify({'error': error_msg}), 400
        elif 'text' in data:
            text = data['text']
            is_valid, error_msg = validate_text_input(text, 'text')
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            texts = [text]
        else:
            return jsonify({'error': 'Missing required field: text or texts'}), 400

        # Get the sentence transformer model from context compacter
        compacter = get_context_compacter()
        
        # Generate embeddings
        embeddings = compacter.sentence_model.encode(texts, convert_to_numpy=True)
        
        # Convert to list for JSON serialization
        embeddings_list = embeddings.tolist()
        
        # Return single embedding or batch
        if len(texts) == 1:
            return jsonify({
                'embedding': embeddings_list[0],
                'dimension': len(embeddings_list[0]),
                'model': 'all-MiniLM-L6-v2'
            })
        else:
            return jsonify({
                'embeddings': embeddings_list,
                'dimension': len(embeddings_list[0]) if embeddings_list else 0,
                'model': 'all-MiniLM-L6-v2',
                'count': len(embeddings_list)
            })

    except Exception as e:
        error_handler.handle_exception(
            e,
            context={
                "endpoint": "/api/generate-embedding",
                "has_data": request.data is not None
            }
        )
        return jsonify({'error': 'Internal server error'}), 500


# Global error handler for uncaught exceptions
@app.errorhandler(Exception)
def handle_uncaught_exception(e):
    """Handle any uncaught exceptions."""
    error_handler.handle_exception(
        e,
        context={
            "endpoint": request.endpoint,
            "method": request.method,
            "url": request.url
        }
    )
    return jsonify({'error': 'Internal server error'}), 500


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
    print("  POST /api/analyze-sentiment - Analyze sentiment with transformer model")
    print("  POST /api/fix-typos - Fix typos and grammar")
    print("  POST /api/generate-embedding - Generate embeddings for semantic search")
    print()

    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )

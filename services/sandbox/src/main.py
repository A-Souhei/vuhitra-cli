import shutil
import sys
import os
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.errors_handler.error_handler import get_error_handler
from heuristics import Heuristics
from heuristics_retriever import HeuristicsRetriever
from insight_extractor import InsightExtractor
from elasticsearch_client import ElasticSearchClient

app = Flask(__name__)

# Initialize error handler
error_handler = get_error_handler()
error_handler.configure(mode=os.getenv('VUHITRA_MODE', 'DEV'), enable_logging=True)

# Initialize heuristics service
heuristics = Heuristics(
    es_host=os.getenv('ELASTICSEARCH_HOST', 'localhost'),
    es_port=int(os.getenv('ELASTICSEARCH_PORT', '9200')),
    es_index=os.getenv('ELASTICSEARCH_INDEX', 'llm_feedback')
)

# Initialize ElasticSearch client for retriever
es_client_instance = ElasticSearchClient(
    host=os.getenv('ELASTICSEARCH_HOST', 'localhost'),
    port=int(os.getenv('ELASTICSEARCH_PORT', '9200')),
    index_name=os.getenv('ELASTICSEARCH_INDEX', 'llm_feedback')
)

# Initialize retriever and insight extractor
retriever = HeuristicsRetriever(
    es_client=es_client_instance.es,
    index_name=os.getenv('ELASTICSEARCH_INDEX', 'llm_feedback'),
    es_client_wrapper=es_client_instance
)
insight_extractor = InsightExtractor(nlp_model=retriever.nlp)

# Configuration
WORKSPACE_DIR = Path("/app/WORKSPACE")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
MAX_PROMPT_LENGTH = 5000  # Maximum prompt length to prevent memory exhaustion


class SandboxException(Exception):
    """Custom exception for sandbox operations"""
    def __init__(self, message, operation=None, status_code=500, **context):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.status_code = status_code
        self.context = context


@app.errorhandler(SandboxException)
def handle_sandbox_exception(e):
    """Handle sandbox exceptions with error handler integration"""
    context = {"operation": e.operation} if e.operation else {}
    context.update(e.context)
    
    error_handler.handle_exception(e, context=context)
    return jsonify({"error": e.message}), e.status_code


@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    """Handle any unexpected exceptions"""
    error_handler.handle_exception(e, context={"operation": "unexpected_error"})
    return jsonify({"error": "Internal server error"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health_status = heuristics.health_check()
    retriever_health = retriever.health_check()
    return jsonify({
        "status": "healthy",
        "service": "sandbox",
        "heuristics": health_status,
        "retriever": retriever_health
    }), 200


@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload a single file to WORKSPACE directory"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    filename = secure_filename(file.filename)
    filepath = WORKSPACE_DIR / filename
    
    try:
        file.save(str(filepath))
    except Exception as e:
        raise SandboxException("Failed to upload file", operation="upload_file", filename=filename) from e
    
    return jsonify({
        "message": "File uploaded successfully",
        "filename": filename,
        "path": str(filepath)
    }), 200


@app.route('/upload-directory', methods=['POST'])
def upload_directory():
    """Upload multiple files (directory contents) to WORKSPACE directory"""
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No valid files provided"}), 400
    
    uploaded_files = []
    failed_files = []
    
    for file in files:
        if file.filename == '':
            continue
        
        # Preserve directory structure if present
        filename = secure_filename(file.filename)
        filepath = WORKSPACE_DIR / filename
        
        try:
            # Create subdirectories if needed
            filepath.parent.mkdir(parents=True, exist_ok=True)
            file.save(str(filepath))
            uploaded_files.append(filename)
        except Exception as e:
            error_handler.handle_exception(e, context={
                "operation": "upload_directory",
                "filename": filename
            })
            failed_files.append({"filename": filename, "error": "Failed to save file"})
    
    response = {
        "message": f"Uploaded {len(uploaded_files)} file(s)",
        "uploaded": uploaded_files
    }
    
    if failed_files:
        response["failed"] = failed_files
        return jsonify(response), 207  # Multi-Status
    
    return jsonify(response), 200


@app.route('/remove/<path:filename>', methods=['DELETE'])
def remove_file(filename):
    """Remove a specific file from WORKSPACE directory"""
    # Secure the filename to prevent directory traversal
    safe_filename = secure_filename(filename)
    filepath = WORKSPACE_DIR / safe_filename
    
    # Ensure the path is within WORKSPACE
    try:
        filepath = filepath.resolve()
        if not str(filepath).startswith(str(WORKSPACE_DIR.resolve())):
            return jsonify({"error": "Invalid file path"}), 400
    except Exception as e:
        error_handler.handle_exception(e, context={
            "operation": "remove_file_path_validation",
            "filename": safe_filename
        })
        return jsonify({"error": "Invalid file path"}), 400
    
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    
    try:
        if filepath.is_file():
            filepath.unlink()
        else:
            raise SandboxException("Not a file", operation="remove_file", 
                                 filename=safe_filename, status_code=400)
    except SandboxException:
        raise
    except Exception as e:
        raise SandboxException("Failed to remove file", operation="remove_file", 
                             filename=safe_filename) from e
    
    return jsonify({
        "message": "File removed successfully",
        "filename": safe_filename
    }), 200


@app.route('/remove-all', methods=['DELETE'])
def remove_all_files():
    """Remove all files from WORKSPACE directory"""
    try:
        removed_count = 0
        for item in WORKSPACE_DIR.iterdir():
            if item.is_file():
                item.unlink()
                removed_count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                removed_count += 1
    except Exception as e:
        raise SandboxException("Failed to remove all files", operation="remove_all_files") from e
    
    return jsonify({
        "message": "All files removed successfully",
        "removed_count": removed_count
    }), 200


@app.route('/list', methods=['GET'])
def list_files():
    """List all files in WORKSPACE directory"""
    try:
        files = []
        for item in WORKSPACE_DIR.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(WORKSPACE_DIR)
                files.append({
                    "name": str(rel_path),
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime
                })
    except Exception as e:
        raise SandboxException("Failed to list files", operation="list_files") from e
    
    return jsonify({
        "workspace": str(WORKSPACE_DIR),
        "file_count": len(files),
        "files": files
    }), 200


@app.route('/analyze/feedback', methods=['POST'])
def analyze_feedback():
    """
    Analyze and store LLM feedback with heuristics.
    Expects JSON: {
        prompt: str,                          # User prompt (required)
        response: str,                        # LLM response (required)
        rating: int,                          # User rating 0-5 (required)
        timestamp: str,                       # ISO timestamp (required)
        execution_time_ms: int,               # Execution time (optional)
        contexted_heuristic_ids: list[str],   # IDs of heuristics in context (optional, for chaining)
        verbose: bool                         # Enable verbose debugging output (optional, default: False)
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        required_fields = ['prompt', 'response', 'rating', 'timestamp']
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Validate optional contexted_heuristic_ids field
        if 'contexted_heuristic_ids' in data:
            if not isinstance(data['contexted_heuristic_ids'], list):
                return jsonify({"error": "contexted_heuristic_ids must be a list"}), 400
            if len(data['contexted_heuristic_ids']) == 0:
                return jsonify({"error": "contexted_heuristic_ids cannot be empty"}), 400
            if len(data['contexted_heuristic_ids']) > 100:
                return jsonify({"error": "contexted_heuristic_ids cannot exceed 100 items"}), 400
            if not all(isinstance(id, str) for id in data['contexted_heuristic_ids']):
                return jsonify({"error": "contexted_heuristic_ids must contain only strings"}), 400

        # Get verbose flag from request
        verbose = data.pop('verbose', False)

        result = heuristics.process_feedback(data, verbose=verbose)
        return jsonify(result), 202  # 202 Accepted (async processing)

    except Exception as e:
        raise SandboxException("Failed to process feedback",
                             operation="analyze_feedback") from e


@app.route('/retrieve/similar', methods=['POST'])
def retrieve_similar():
    """
    Retrieve the most similar heuristic for a given prompt.

    Expects JSON: {
        prompt: str,              # User's input prompt (required)
        min_rating: int,          # Minimum rating threshold (optional, default: 3)
        verbose: bool             # Enable verbose debugging output (optional, default: False)
    }

    Returns: {
        matched_heuristic: dict,  # The best matching document
        confidence_score: float,  # Overall confidence (0-1)
        insights: dict,           # Extracted insights
        scoring_breakdown: dict,  # Individual scores for each method
        chain: list               # Chain of parent heuristics (if verbose)
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        if 'prompt' not in data:
            return jsonify({"error": "Missing required field: prompt"}), 400

        prompt = data['prompt']
        min_rating = data.get('min_rating', 3)
        verbose = data.get('verbose', False)

        # Validate inputs
        if not isinstance(prompt, str) or len(prompt.strip()) == 0:
            return jsonify({"error": "Prompt must be a non-empty string"}), 400

        # Validate prompt length to prevent memory exhaustion
        if len(prompt) > MAX_PROMPT_LENGTH:
            return jsonify({"error": f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"}), 400

        if not isinstance(min_rating, int) or min_rating < 0 or min_rating > 5:
            return jsonify({"error": "min_rating must be an integer between 0 and 5"}), 400

        # Retrieve best match
        result = retriever.retrieve_best_match(
            prompt=prompt,
            min_rating=min_rating
        )

        if not result:
            return jsonify({
                "message": "No suitable match found",
                "matched_heuristic": None,
                "confidence_score": 0.0,
                "insights": None
            }), 200

        # Extract insights from the matched heuristic and its chain
        chain = result.get('chain', [])
        if chain:
            insights = insight_extractor.extract_chain_insights(
                matched_heuristic=result['matched_heuristic'],
                chain=chain
            )
        else:
            insights = insight_extractor.extract_insights(result['matched_heuristic'])

        response_data = {
            "matched_heuristic": result['matched_heuristic'],
            "confidence_score": result['confidence_score'],
            "insights": insights,
            "scoring_breakdown": result['scoring_breakdown'],
            "chain_length": len(chain),
            "has_chain": len(chain) > 0
        }

        # Add verbose debugging information
        if verbose:
            response_data["chain"] = chain
            response_data["retrieval_metadata"] = {
                "total_candidates": result.get('total_candidates', 0),
                "stage1_filtered": result.get('stage1_filtered', 0),
                "stage2_filtered": result.get('stage2_filtered', 0),
                "final_selected": 1 if result['matched_heuristic'] else 0
            }

        return jsonify(response_data), 200

    except Exception as e:
        raise SandboxException("Failed to retrieve similar heuristic",
                             operation="retrieve_similar") from e


@app.route('/validate/response', methods=['POST'])
def validate_response():
    """
    Validate a response by comparing it with similar past interactions.

    This is an optional post-LLM check to assess response quality
    against historical high-quality responses.

    Expects JSON: {
        prompt: str,              # User's input prompt (required)
        response: str,            # LLM's generated response (required)
        original_rating: int      # Optional rating if available
    }

    Returns: {
        quality_assessment: str,  # Overall quality assessment
        similar_matches: list,    # List of similar past interactions
        recommendations: list     # Suggestions for improvement
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        required_fields = ['prompt', 'response']
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        prompt = data['prompt']
        response = data['response']
        original_rating = data.get('original_rating')

        # Validate prompt and response
        if not isinstance(prompt, str) or len(prompt.strip()) == 0:
            return jsonify({"error": "Prompt must be a non-empty string"}), 400

        if not isinstance(response, str) or len(response.strip()) == 0:
            return jsonify({"error": "Response must be a non-empty string"}), 400

        # Validate original_rating if provided
        if original_rating is not None:
            if not isinstance(original_rating, int) or original_rating < 0 or original_rating > 5:
                return jsonify({"error": "original_rating must be an integer between 0 and 5"}), 400

        # Find similar high-quality responses
        match_result = retriever.retrieve_best_match(
            prompt=prompt,
            min_rating=4  # Only compare with high-quality responses
        )

        if not match_result:
            return jsonify({
                "quality_assessment": "No similar high-quality responses found for comparison",
                "similar_matches": [],
                "recommendations": ["Continue building history for this type of query"]
            }), 200

        # Analyze the match
        matched_doc = match_result['matched_heuristic']
        confidence = match_result['confidence_score']

        # Generate quality assessment based on confidence
        recommendations = []

        if confidence > 0.8:
            quality_assessment = "Excellent - Very similar to past high-quality response"
        elif confidence > 0.6:
            quality_assessment = "Good - Comparable to past successful responses"
            recommendations.append("Consider incorporating techniques from similar past response")
        else:
            quality_assessment = "Moderate - Less similar to past high-quality responses"
            recommendations.append("Review similar past response for alternative approaches")

        # Extract insights from matched response
        insights = insight_extractor.extract_insights(matched_doc)

        return jsonify({
            "quality_assessment": quality_assessment,
            "similar_matches": [{
                "prompt": matched_doc.get('prompt'),
                "rating": matched_doc.get('rating'),
                "confidence": confidence,
                "key_techniques": insights.get('key_techniques', [])
            }],
            "recommendations": recommendations
        }), 200

    except Exception as e:
        raise SandboxException("Failed to validate response",
                             operation="validate_response") from e


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

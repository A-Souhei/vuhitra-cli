import shutil
import sys
import os
import logging
import io
import zipfile
import redis
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from threading import Thread
import time as time_module

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.errors_handler.error_handler import get_error_handler
from heuristics import Heuristics
from heuristics_retriever import HeuristicsRetriever
from heuristics_pruner import HeuristicsPruner
from insight_extractor import InsightExtractor
from elasticsearch_client import ElasticSearchClient
from heuristics_config_loader import HeuristicsConfigLoader

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def sanitize_path(path_str):
    """
    Sanitize path to prevent directory traversal while preserving directory structure.

    Args:
        path_str: Path string to sanitize

    Returns:
        Sanitized path string safe for use in file operations

    Removes:
        - Leading/trailing slashes
        - '..' parent directory references
        - Absolute paths (leading '/')

    Preserves:
        - Directory separators (/)
        - File and folder names
    """
    # Remove leading/trailing whitespace and slashes
    path_str = path_str.strip().strip('/')

    # Split into parts and filter out dangerous components
    parts = []
    for part in path_str.split('/'):
        # Skip empty parts, '.', and '..'
        if part and part != '.' and part != '..':
            # Sanitize each component individually to prevent special characters
            safe_part = secure_filename(part)
            if safe_part:  # Only add if sanitization didn't remove everything
                parts.append(safe_part)

    # Rejoin with forward slashes
    return '/'.join(parts) if parts else ''

# Configure Flask app with template and static folders
app = Flask(__name__, 
            template_folder='/app/templates',
            static_folder='/app/static')

# Initialize error handler
error_handler = get_error_handler()
error_handler.configure(mode=os.getenv('VUHITRA_MODE', 'DEV'), enable_logging=True)

# Initialize Redis connection for mirror tracking
redis_client = None
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info("Connected to Redis for mirror tracking")
except Exception as e:
    logger.warning(f"Could not connect to Redis: {e}. Mirror tracking will be disabled.")
    redis_client = None

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
    es_client_wrapper=es_client_instance,
    transformer_host=os.getenv('TRANSFORMER_HOST', 'transformer'),
    transformer_port=int(os.getenv('TRANSFORMER_PORT', '5050'))
)
# InsightExtractor loads its own spaCy model for NLP tasks (e.g., entity extraction, linguistic analysis).
# Note: The retriever no longer depends on spaCy; it uses transformer embeddings for semantic similarity.
# Only InsightExtractor requires spaCy for text analysis and insight formatting.
insight_extractor = InsightExtractor()

# Initialize heuristics pruner
config_loader = HeuristicsConfigLoader()
pruner = HeuristicsPruner(
    es_client=es_client_instance.es,
    index_name=os.getenv('ELASTICSEARCH_INDEX', 'llm_feedback'),
    retriever=retriever,
    config_loader=config_loader
)

# Configuration
WORKSPACE_DIR = Path("/app/WORKSPACE")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
MIRRORS_DIR = Path("/app/WORKSPACE/mirrors")
MIRRORS_DIR.mkdir(parents=True, exist_ok=True)

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


@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 Not Found errors with beautiful error page"""
    # Check if request wants JSON (API endpoints)
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found", "path": request.path}), 404

    # Otherwise return HTML 404 page
    return render_template('404.html'), 404


# Redis mirror tracking helper functions
def add_mirror_to_redis(target_name, is_file, file_count):
    """Register a mirror in Redis with metadata"""
    if not redis_client:
        logger.debug("Redis not available, skipping mirror registration")
        return

    try:
        mirror_data = {
            'name': target_name,
            'type': 'file' if is_file else 'directory',
            'file_count': file_count,
            'created_at': datetime.now().isoformat(),
            'sync_status': 'synced',  # Initially synced since just created
            'last_checked': datetime.now().isoformat()
        }
        redis_client.hset(f'mirror:{target_name}', mapping=mirror_data)
        logger.info(f"Registered mirror '{target_name}' in Redis")
    except Exception as e:
        logger.warning(f"Failed to register mirror in Redis: {e}")


def remove_mirror_from_redis(target_name):
    """Remove a mirror from Redis registry"""
    if not redis_client:
        logger.debug("Redis not available, skipping mirror removal")
        return

    try:
        redis_client.delete(f'mirror:{target_name}')
        logger.info(f"Removed mirror '{target_name}' from Redis")
    except Exception as e:
        logger.warning(f"Failed to remove mirror from Redis: {e}")


def get_all_mirrors_from_redis():
    """Get all registered mirrors from Redis"""
    if not redis_client:
        return []

    try:
        mirrors = []
        # Get all keys matching mirror:*
        for key in redis_client.scan_iter(match='mirror:*'):
            mirror_data = redis_client.hgetall(key)
            if mirror_data:
                mirrors.append(mirror_data)
        return mirrors
    except Exception as e:
        logger.warning(f"Failed to get mirrors from Redis: {e}")
        return []


def update_mirror_last_checked(target_name):
    """Update only the last_checked timestamp in Redis (for cron monitoring)"""
    if not redis_client:
        logger.debug("Redis not available, skipping last_checked update")
        return

    try:
        # Check if mirror exists
        if not redis_client.exists(f'mirror:{target_name}'):
            logger.warning(f"Mirror '{target_name}' not found in Redis")
            return

        # Only update last checked time, do NOT touch sync_status
        redis_client.hset(f'mirror:{target_name}', 'last_checked', datetime.now().isoformat())
        logger.debug(f"Updated last_checked for mirror '{target_name}'")
    except Exception as e:
        logger.warning(f"Failed to update last_checked in Redis: {e}")


def update_mirror_sync_status(target_name, synced, differences=None):
    """Update sync status in Redis (called by CLI after actual sync comparison)"""
    if not redis_client:
        logger.debug("Redis not available, skipping sync status update")
        return

    try:
        # Check if mirror exists
        if not redis_client.exists(f'mirror:{target_name}'):
            logger.warning(f"Mirror '{target_name}' not found in Redis")
            return

        # Update sync status and last checked time
        updates = {
            'sync_status': 'synced' if synced else 'not_synced',
            'last_checked': datetime.now().isoformat()
        }

        # Store differences if not synced
        if not synced and differences:
            updates['differences'] = json.dumps(differences)
        elif synced and redis_client.hexists(f'mirror:{target_name}', 'differences'):
            # Remove differences field if now synced
            redis_client.hdel(f'mirror:{target_name}', 'differences')

        redis_client.hset(f'mirror:{target_name}', mapping=updates)
        logger.info(f"Updated sync status for mirror '{target_name}': {updates['sync_status']}")
    except Exception as e:
        logger.warning(f"Failed to update sync status in Redis: {e}")


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
        min_rating: int,          # Minimum rating threshold (optional, default: 4)
        verbose: bool,            # Enable verbose debugging output (optional, default: False)
        negative_weight_boost: float  # Boost for negative heuristics (optional, default: 0.0, range: 0.0-1.0)
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
        min_rating = data.get('min_rating', 4)
        verbose = data.get('verbose', False)
        negative_weight_boost = data.get('negative_weight_boost', 0.0)

        # Validate inputs
        if not isinstance(prompt, str) or len(prompt.strip()) == 0:
            return jsonify({"error": "Prompt must be a non-empty string"}), 400

        # Validate prompt length to prevent memory exhaustion
        if len(prompt) > MAX_PROMPT_LENGTH:
            return jsonify({"error": f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"}), 400

        if not isinstance(min_rating, int) or min_rating < 0 or min_rating > 5:
            return jsonify({"error": "min_rating must be an integer between 0 and 5"}), 400

        if not isinstance(negative_weight_boost, (int, float)) or negative_weight_boost < 0.0 or negative_weight_boost > 1.0:
            return jsonify({"error": "negative_weight_boost must be a number between 0.0 and 1.0"}), 400

        if verbose and negative_weight_boost > 0:
            logger.info(f"Auto-iteration mode: negative_weight_boost={negative_weight_boost:.2f}")

        # Retrieve best match - try positive heuristics first
        result = retriever.retrieve_best_match(
            prompt=prompt,
            min_rating=min_rating,
            negative_weight_boost=negative_weight_boost
        )

        is_negative = False

        # If no positive match found, try negative heuristics (anti-patterns)
        if not result:
            if verbose:
                logger.info("No positive heuristic found, trying negative heuristics (anti-patterns)")

            result = retriever.retrieve_negative_heuristics(
                prompt=prompt,
                max_rating=retriever.MAX_RATING_NEGATIVE,  # Use configured value
                negative_weight_boost=negative_weight_boost,
                verbose=verbose
            )

            if result:
                is_negative = True
                if verbose:
                    logger.info(f"Negative heuristic found with confidence {result.get('confidence_score', 0):.3f}")

        if not result:
            return jsonify({
                "message": "No suitable match found (neither positive nor negative)",
                "matched_heuristic": None,
                "confidence_score": 0.0,
                "insights": None
            }), 200

        # Extract insights based on whether it's positive or negative
        chain = result.get('chain', [])

        if is_negative or result.get('is_negative', False):
            # Extract negative insights (anti-patterns)
            # If chain exists, include all parent anti-patterns for complete failure history
            if chain:
                insights = insight_extractor.extract_negative_chain_insights(
                    matched_heuristic=result['matched_heuristic'],
                    chain=chain
                )
            else:
                insights = insight_extractor.extract_negative_insights(result['matched_heuristic'])
        elif chain:
            # Extract chain insights for positive heuristics
            insights = insight_extractor.extract_chain_insights(
                matched_heuristic=result['matched_heuristic'],
                chain=chain
            )
        else:
            # Extract standard positive insights
            insights = insight_extractor.extract_insights(result['matched_heuristic'])

        response_data = {
            "matched_heuristic": result['matched_heuristic'],
            "confidence_score": result['confidence_score'],
            "insights": insights,
            "scoring_breakdown": result['scoring_breakdown'],
            "chain_length": len(chain),
            "has_chain": len(chain) > 0,
            "is_negative": is_negative or result.get('is_negative', False)
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


@app.route('/admin/prune-heuristics', methods=['POST'])
def prune_heuristics():
    """
    Manually trigger auto-pruning of unretrievable heuristics.

    This endpoint removes heuristics that are no longer retrievable due to
    the existence of higher-rated similar heuristics.

    Expects JSON: {
        verbose: bool  # Enable detailed logging (optional, default: False)
    }

    Returns: {
        enabled: bool,          # Whether pruning is enabled
        total_checked: int,     # Total heuristics examined
        pruned_count: int,      # Number of heuristics removed
        errors: int            # Number of errors encountered
    }
    """
    try:
        data = request.get_json() or {}
        verbose = data.get('verbose', False)

        logger.info("Manual prune-heuristics request received")

        # Run pruning
        result = pruner.prune_unretrievable_heuristics(verbose=verbose)

        return jsonify(result), 200

    except Exception as e:
        raise SandboxException("Failed to prune heuristics",
                             operation="prune_heuristics") from e


@app.route('/sync', methods=['POST'])
def sync_to_mirror():
    """
    Synchronize files from host to sandbox mirror.

    Expects multipart/form-data with:
        - files: Multiple files to sync
        - target_name: Target directory/file name in mirrors

    This will:
    - Update existing files
    - Add new files
    - Delete files in mirror that don't exist in source

    Returns: {
        message: str,           # Status message
        target_name: str,       # Name of mirrored directory/file
        synced: list,          # List of synced files
        deleted: list          # List of deleted files
    }
    """
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400

    target_name = request.form.get('target_name')
    if not target_name:
        return jsonify({"error": "No target_name provided"}), 400

    # Sanitize the target name while preserving directory structure
    safe_target = sanitize_path(target_name)
    if not safe_target:
        return jsonify({"error": "Invalid target_name"}), 400
    target_path = MIRRORS_DIR / safe_target

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No valid files provided"}), 400

    synced_files = []
    failed_files = []

    try:
        # Create target directory if it doesn't exist
        target_path.mkdir(parents=True, exist_ok=True)

        # Track uploaded file names
        uploaded_names = set()

        # Upload/update files
        for file in files:
            if file.filename == '':
                continue

            # Preserve relative paths
            filename = file.filename
            uploaded_names.add(filename)
            filepath = target_path / filename

            try:
                # Create subdirectories if needed
                filepath.parent.mkdir(parents=True, exist_ok=True)
                file.save(str(filepath))
                synced_files.append(filename)
            except Exception as e:
                error_handler.handle_exception(e, context={
                    "operation": "sync_to_mirror",
                    "filename": filename,
                    "target": safe_target
                })
                failed_files.append({"filename": filename, "error": "Failed to save file"})

        # Delete files in mirror that weren't uploaded (they were deleted from source)
        deleted_files = []
        for item in target_path.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(target_path)
                if str(rel_path) not in uploaded_names:
                    try:
                        item.unlink()
                        deleted_files.append(str(rel_path))
                    except Exception as e:
                        error_handler.handle_exception(e, context={
                            "operation": "sync_delete_orphaned",
                            "filename": str(rel_path),
                            "target": safe_target
                        })

        response = {
            "message": f"Synced {len(synced_files)} file(s), deleted {len(deleted_files)} orphaned file(s)",
            "target_name": safe_target,
            "synced": synced_files,
            "deleted": deleted_files
        }

        # Register mirror in Redis
        # Check if this is a single-file mirror (directory with only one file and no subdirectories)
        all_files = list(target_path.rglob('*'))
        files_only = [f for f in all_files if f.is_file()]
        is_file = len(files_only) == 1 and len(all_files) == 1
        file_count = len(synced_files)
        add_mirror_to_redis(safe_target, is_file, file_count)

        if failed_files:
            response["failed"] = failed_files
            return jsonify(response), 207  # Multi-Status

        return jsonify(response), 200

    except Exception as e:
        raise SandboxException("Failed to sync to mirror",
                             operation="sync_to_mirror",
                             target=safe_target) from e


@app.route('/revert-sync', methods=['POST'])
def revert_sync_from_mirror():
    """
    Synchronize files from sandbox mirror back to requestor.

    Expects JSON: {
        target_name: str  # Name of mirrored directory/file
    }

    Returns: {
        message: str,           # Status message
        target_name: str,       # Name of mirrored directory/file
        file_count: int,        # Number of files
        files: list            # List of file info dicts
    }
    """
    data = request.get_json()
    if not data or 'target_name' not in data:
        return jsonify({"error": "No target_name provided"}), 400

    target_name = data['target_name']
    safe_target = sanitize_path(target_name)
    if not safe_target:
        return jsonify({"error": "Invalid target_name"}), 400
    target_path = MIRRORS_DIR / safe_target

    # Ensure the path is within MIRRORS_DIR
    try:
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(MIRRORS_DIR.resolve())):
            return jsonify({"error": "Invalid target path"}), 400
    except Exception as e:
        error_handler.handle_exception(e, context={
            "operation": "revert_sync_path_validation",
            "target": safe_target
        })
        return jsonify({"error": "Invalid target path"}), 400

    if not target_path.exists():
        return jsonify({"error": "Mirror not found"}), 404

    try:
        files_info = []

        if target_path.is_file():
            # Single file
            files_info.append({
                "name": target_path.name,
                "size": target_path.stat().st_size,
                "modified": target_path.stat().st_mtime,
                "is_file": True
            })
        else:
            # Directory - get all files and directories recursively
            for item in target_path.rglob('*'):
                rel_path = item.relative_to(target_path)
                is_file = item.is_file()
                files_info.append({
                    "name": str(rel_path),
                    "size": item.stat().st_size if is_file else 0,
                    "modified": item.stat().st_mtime,
                    "is_file": is_file
                })

        return jsonify({
            "message": "Mirror contents retrieved successfully",
            "target_name": safe_target,
            "file_count": len(files_info),
            "files": files_info,
            "mirror_path": str(target_path)
        }), 200

    except Exception as e:
        raise SandboxException("Failed to revert-sync from mirror",
                             operation="revert_sync_from_mirror",
                             target=safe_target) from e


@app.route('/download-mirror/<path:target_name>', methods=['GET'])
def download_mirror(target_name):
    """
    Download files from a sandbox mirror.

    For single files: Returns the file directly
    For directories: Returns a zip archive containing all files

    Args:
        target_name: Name of the mirror to download

    Query parameters:
        file_path: Optional specific file path within the mirror (for single file download)

    Returns:
        File download or zip archive
    """
    safe_target = sanitize_path(target_name)
    if not safe_target:
        return jsonify({"error": "Invalid target_name"}), 400
    target_path = MIRRORS_DIR / safe_target

    # Get optional file_path parameter for downloading specific files
    file_path = request.args.get('file_path')

    # Ensure the path is within MIRRORS_DIR
    try:
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(MIRRORS_DIR.resolve())):
            return jsonify({"error": "Invalid target path"}), 400
    except Exception as e:
        error_handler.handle_exception(e, context={
            "operation": "download_mirror_path_validation",
            "target": safe_target
        })
        return jsonify({"error": "Invalid target path"}), 400

    if not target_path.exists():
        return jsonify({"error": "Mirror not found"}), 404

    try:
        # If file_path is specified, download that specific file
        if file_path:
            file_to_download = target_path / file_path
            file_to_download = file_to_download.resolve()

            # Ensure the file is within the mirror directory
            if not str(file_to_download).startswith(str(target_path)):
                return jsonify({"error": "Invalid file path"}), 400

            if not file_to_download.exists() or not file_to_download.is_file():
                return jsonify({"error": "File not found"}), 404

            return send_file(
                str(file_to_download),
                as_attachment=True,
                download_name=file_to_download.name
            )

        # If target is a single file, return it directly
        if target_path.is_file():
            return send_file(
                str(target_path),
                as_attachment=True,
                download_name=target_path.name
            )

        # If target is a directory, create a zip archive
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item_path in target_path.rglob('*'):
                if item_path.is_file():
                    # Get path relative to the mirror directory
                    arcname = item_path.relative_to(target_path)
                    zf.write(item_path, arcname=str(arcname))

        memory_file.seek(0)

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{safe_target}.zip"
        )

    except Exception as e:
        raise SandboxException("Failed to download mirror",
                             operation="download_mirror",
                             target=safe_target) from e


@app.route('/mirrors/remove/<path:target_name>', methods=['DELETE'])
def remove_mirror(target_name):
    """
    Remove a mirror from the sandbox.

    Args:
        target_name: Name of the mirror to remove

    Returns: {
        message: str,           # Status message
        target_name: str        # Name of removed mirror
    }
    """
    # Sanitize the target name while preserving directory structure
    safe_target = sanitize_path(target_name)
    if not safe_target:
        return jsonify({"error": "Invalid target_name"}), 400
    target_path = MIRRORS_DIR / safe_target

    # Validate path is within MIRRORS_DIR
    try:
        resolved_path = target_path.resolve()
        if not str(resolved_path).startswith(str(MIRRORS_DIR.resolve())):
            return jsonify({"error": "Invalid mirror path"}), 400
    except Exception as e:
        error_handler.handle_exception(e, context={
            "operation": "remove_mirror_path_validation",
            "target": safe_target
        })
        return jsonify({"error": "Invalid mirror path"}), 400

    if not target_path.exists():
        return jsonify({"error": "Mirror not found"}), 404

    try:
        # Remove the mirror (file or directory)
        if target_path.is_file():
            target_path.unlink()
        elif target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            return jsonify({"error": "Invalid mirror type"}), 400

        # Remove from Redis
        remove_mirror_from_redis(safe_target)

        return jsonify({
            "message": f"Mirror '{safe_target}' removed successfully",
            "target_name": safe_target
        }), 200

    except Exception as e:
        raise SandboxException("Failed to remove mirror",
                             operation="remove_mirror",
                             target=safe_target) from e


@app.route('/mirror-exists/<path:target_name>', methods=['GET'])
def mirror_exists(target_name):
    """
    Check if a mirror exists in the sandbox.

    Args:
        target_name: Name of the mirror to check

    Returns: {
        exists: bool,           # Whether the mirror exists
        target_name: str,       # Name of the mirror
        is_file: bool,          # True if it's a file, False if directory (only if exists)
        file_count: int         # Number of files (only for directories)
    }
    """
    safe_target = secure_filename(target_name)
    target_path = MIRRORS_DIR / safe_target

    # Ensure the path is within MIRRORS_DIR
    try:
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(MIRRORS_DIR.resolve())):
            return jsonify({"error": "Invalid target path"}), 400
    except Exception as e:
        error_handler.handle_exception(e, context={
            "operation": "mirror_exists_path_validation",
            "target": safe_target
        })
        return jsonify({"error": "Invalid target path"}), 400

    if not target_path.exists():
        return jsonify({
            "exists": False,
            "target_name": safe_target
        }), 200

    try:
        is_file = target_path.is_file()
        file_count = 0

        if not is_file:
            # Count files in directory
            file_count = sum(1 for item in target_path.rglob('*') if item.is_file())

        return jsonify({
            "exists": True,
            "target_name": safe_target,
            "is_file": is_file,
            "file_count": file_count if not is_file else 1
        }), 200

    except Exception as e:
        raise SandboxException("Failed to check mirror existence",
                             operation="mirror_exists",
                             target=safe_target) from e


@app.route('/mirror-synced', methods=['POST'])
def mirror_synced():
    """
    Check if host files are in sync with sandbox mirror.

    Expects JSON: {
        target_name: str,       # Name of the mirror
        files: list             # List of file info dicts with 'name', 'size', 'modified'
    }

    Returns: {
        synced: bool,           # Whether files are in sync
        target_name: str,       # Name of the mirror
        differences: dict       # Details about differences (if not synced)
    }
    """
    data = request.get_json()
    if not data or 'target_name' not in data:
        return jsonify({"error": "No target_name provided"}), 400

    if 'files' not in data:
        return jsonify({"error": "No files list provided"}), 400

    target_name = data['target_name']
    host_files = data['files']

    safe_target = secure_filename(target_name)
    target_path = MIRRORS_DIR / safe_target

    # Ensure the path is within MIRRORS_DIR
    try:
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(MIRRORS_DIR.resolve())):
            return jsonify({"error": "Invalid target path"}), 400
    except Exception as e:
        error_handler.handle_exception(e, context={
            "operation": "mirror_synced_path_validation",
            "target": safe_target
        })
        return jsonify({"error": "Invalid target path"}), 400

    if not target_path.exists():
        return jsonify({"error": "Mirror not found"}), 404

    try:
        # Build a dict of host files for comparison
        host_files_dict = {}
        for file_info in host_files:
            name = file_info.get('name', '')
            # Normalize path separators
            normalized_name = name.replace('\\', '/')
            host_files_dict[normalized_name] = {
                'size': file_info.get('size', 0),
                'modified': file_info.get('modified', 0)
            }

        # Get mirror files
        mirror_files_dict = {}
        if target_path.is_file():
            mirror_files_dict[target_path.name] = {
                'size': target_path.stat().st_size,
                'modified': target_path.stat().st_mtime
            }
        else:
            for item in target_path.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(target_path)
                    normalized_name = str(rel_path).replace('\\', '/')
                    mirror_files_dict[normalized_name] = {
                        'size': item.stat().st_size,
                        'modified': item.stat().st_mtime
                    }

        # Compare files
        only_in_host = []
        only_in_mirror = []
        different_size = []
        different_modified = []

        # Check files in host
        for name, info in host_files_dict.items():
            if name not in mirror_files_dict:
                only_in_host.append(name)
            else:
                mirror_info = mirror_files_dict[name]
                if info['size'] != mirror_info['size']:
                    different_size.append({
                        'name': name,
                        'host_size': info['size'],
                        'mirror_size': mirror_info['size']
                    })
                # Note: We're being lenient with modification times (allowing small differences)
                # because file transfers can slightly change mtimes
                elif abs(info['modified'] - mirror_info['modified']) > 2:
                    different_modified.append({
                        'name': name,
                        'host_modified': info['modified'],
                        'mirror_modified': mirror_info['modified']
                    })

        # Check files only in mirror
        for name in mirror_files_dict:
            if name not in host_files_dict:
                only_in_mirror.append(name)

        # Determine if synced
        synced = (
            len(only_in_host) == 0 and
            len(only_in_mirror) == 0 and
            len(different_size) == 0 and
            len(different_modified) == 0
        )

        response = {
            "synced": synced,
            "target_name": safe_target
        }

        if not synced:
            response["differences"] = {
                "only_in_host": only_in_host,
                "only_in_mirror": only_in_mirror,
                "different_size": different_size,
                "different_modified": different_modified
            }

        return jsonify(response), 200

    except Exception as e:
        raise SandboxException("Failed to check mirror sync status",
                             operation="mirror_synced",
                             target=safe_target) from e


@app.route('/mirror-list', methods=['GET'])
def mirror_list():
    """
    Get list of all registered mirrors from Redis.

    Returns: {
        mirrors: list           # List of mirror metadata dicts
    }

    Each mirror dict contains:
        - name: str
        - type: str (file or directory)
        - file_count: int
        - created_at: str (ISO format)
        - sync_status: str (synced or not_synced)
        - last_checked: str (ISO format)
        - differences: dict (optional, if not_synced)
    """
    try:
        mirrors = get_all_mirrors_from_redis()

        return jsonify({
            "mirrors": mirrors
        }), 200

    except Exception as e:
        raise SandboxException("Failed to list mirrors",
                             operation="mirror_list") from e


# Background cron job to check mirror sync status
def mirror_sync_monitor():
    """
    Background job that periodically checks sync status for all mirrors.
    Updates Redis with the latest sync status.
    """
    logger.info("Mirror sync monitor started")

    # Check interval in seconds (default: 10 seconds, minimum: 10, maximum: 3600)
    try:
        check_interval = int(os.getenv('MIRROR_SYNC_CHECK_INTERVAL', '10'))
        # Validate bounds: minimum 10 seconds, maximum 1 hour
        if check_interval < 10:
            logger.warning(f"MIRROR_SYNC_CHECK_INTERVAL too low ({check_interval}s), using minimum 10s")
            check_interval = 10
        elif check_interval > 3600:
            logger.warning(f"MIRROR_SYNC_CHECK_INTERVAL too high ({check_interval}s), using maximum 3600s")
            check_interval = 3600
    except ValueError:
        logger.warning("Invalid MIRROR_SYNC_CHECK_INTERVAL, using default 10s")
        check_interval = 10

    while True:
        try:
            # Wait before first check
            time_module.sleep(check_interval)

            if not redis_client:
                logger.debug("Redis not available, skipping sync check")
                continue

            mirrors = get_all_mirrors_from_redis()
            if not mirrors:
                logger.debug("No mirrors to check")
                continue

            logger.info(f"Checking sync status for {len(mirrors)} mirror(s)")

            for mirror in mirrors:
                try:
                    mirror_name = mirror.get('name')
                    if not mirror_name:
                        continue

                    # Check if mirror still exists in filesystem
                    safe_name = sanitize_path(mirror_name)
                    if not safe_name:
                        logger.warning(f"Invalid mirror name: {mirror_name}")
                        continue
                    mirror_path = MIRRORS_DIR / safe_name

                    if not mirror_path.exists():
                        logger.warning(f"Mirror '{mirror_name}' not found in filesystem")
                        # Could remove from Redis here, but we'll leave it for manual cleanup
                        continue

                    # Get mirror files for comparison
                    mirror_files_dict = {}
                    if mirror_path.is_file():
                        mirror_files_dict[mirror_path.name] = {
                            'size': mirror_path.stat().st_size,
                            'modified': mirror_path.stat().st_mtime
                        }
                    else:
                        for item in mirror_path.rglob('*'):
                            if item.is_file():
                                rel_path = item.relative_to(mirror_path)
                                normalized_name = str(rel_path).replace('\\', '/')
                                mirror_files_dict[normalized_name] = {
                                    'size': item.stat().st_size,
                                    'modified': item.stat().st_mtime
                                }

                    # Cron can only update last_checked timestamp
                    # Sync status is managed by CLI after actual file comparison with host
                    update_mirror_last_checked(mirror_name)

                    logger.debug(f"Checked mirror '{mirror_name}': {len(mirror_files_dict)} files")

                except Exception as e:
                    logger.error(f"Error checking mirror '{mirror.get('name', 'unknown')}': {e}")
                    continue

            logger.info(f"Sync check completed for {len(mirrors)} mirror(s)")

        except Exception as e:
            logger.error(f"Error in mirror sync monitor: {e}")
            # Continue running despite errors
            continue


@app.route('/mirrors', methods=['GET'])
def mirror_web_interface():
    """Web interface for managing mirrors"""
    return render_template('mirrors.html')


@app.route('/home', methods=['GET'])
@app.route('/', methods=['GET'])
def home_interface():
    """Home page with navigation to all context management pages"""
    return render_template('home.html')


@app.route('/eternals', methods=['GET'])
def eternals_interface():
    """Web interface for managing eternal contexts"""
    return render_template('eternals.html')


@app.route('/pillars', methods=['GET'])
def pillars_interface():
    """Web interface for managing pillar contexts"""
    return render_template('pillars.html')


@app.route('/ephemerals', methods=['GET'])
def ephemerals_interface():
    """Web interface for managing ephemeral contexts"""
    return render_template('ephemerals.html')


@app.route('/vanishers', methods=['GET'])
def vanishers_interface():
    """Web interface for managing vanisher contexts"""
    return render_template('vanishers.html')


# API endpoints for context management (placeholders for future implementation)
@app.route('/api/contexts/eternals', methods=['GET'])
def api_get_eternals():
    """API endpoint to get eternal contexts"""
    return jsonify({
        'contexts': [],
        'message': 'This endpoint requires the CLI to be running with eternal contexts enabled'
    })


@app.route('/api/contexts/pillars', methods=['GET'])
def api_get_pillars():
    """API endpoint to get pillar contexts"""
    return jsonify({
        'contexts': [],
        'message': 'This endpoint requires the CLI to be running in coding mode (--coding flag)'
    })


@app.route('/api/contexts/ephemerals', methods=['GET'])
def api_get_ephemerals():
    """API endpoint to get ephemeral contexts"""
    return jsonify({
        'contexts': [],
        'message': 'This endpoint requires the CLI to be running with ephemeral contexts enabled'
    })


@app.route('/api/contexts/vanishers', methods=['GET'])
def api_get_vanishers():
    """API endpoint to get vanisher contexts"""
    return jsonify({
        'contexts': [],
        'message': 'This endpoint requires the CLI to be running in coding mode (--coding flag)'
    })


# MCP Management Functions
def get_coding_mode_status():
    """Check if CLI is in coding mode"""
    # Check environment variable or Redis flag
    return os.getenv('VUHITRA_CODING_MODE', 'false').lower() == 'true'


def get_all_mcps_from_redis():
    """Get all registered MCPs from Redis"""
    if not redis_client:
        return []

    try:
        mcps = []
        # Get all keys matching mcp:*
        for key in redis_client.scan_iter(match='mcp:*'):
            mcp_data = redis_client.hgetall(key)
            if mcp_data:
                mcps.append(mcp_data)
        return mcps
    except Exception as e:
        logger.warning(f"Failed to get MCPs from Redis: {e}")
        return []


def register_mcp_in_redis(mcp_id, name, description, tools_count=0, resources_count=0, always_enabled=False):
    """Register an MCP in Redis"""
    if not redis_client:
        logger.debug("Redis not available, skipping MCP registration")
        return

    try:
        mcp_data = {
            'id': mcp_id,
            'name': name,
            'description': description,
            'tools_count': tools_count,
            'resources_count': resources_count,
            'enabled': 'true' if always_enabled else 'false',
            'always_enabled': 'true' if always_enabled else 'false',
            'registered_at': datetime.now().isoformat()
        }
        redis_client.hset(f'mcp:{mcp_id}', mapping=mcp_data)
        logger.info(f"Registered MCP '{mcp_id}' in Redis")
    except Exception as e:
        logger.warning(f"Failed to register MCP in Redis: {e}")


def toggle_mcp_enabled(mcp_id, enabled):
    """Toggle MCP enabled status (only if not always_enabled)"""
    if not redis_client:
        return {'success': False, 'error': 'Redis not available'}

    try:
        mcp_key = f'mcp:{mcp_id}'
        if not redis_client.exists(mcp_key):
            return {'success': False, 'error': 'MCP not found'}

        mcp_data = redis_client.hgetall(mcp_key)
        if mcp_data.get('always_enabled') == 'true':
            return {'success': False, 'error': 'This MCP is always enabled and cannot be disabled'}

        redis_client.hset(mcp_key, 'enabled', 'true' if enabled else 'false')
        return {'success': True}
    except Exception as e:
        logger.warning(f"Failed to toggle MCP: {e}")
        return {'success': False, 'error': str(e)}


# Initialize Mirror+Vanisher MCP in Redis
# This MCP is always enabled in coding mode
if redis_client:
    is_coding_mode = get_coding_mode_status()
    register_mcp_in_redis(
        mcp_id='mirror-vanisher-dev',
        name='Mirror+Vanisher Development MCP',
        description='LLM-driven development operations on mirrored directories loaded into context',
        tools_count=18,  # Based on our test results
        resources_count=0,
        always_enabled=is_coding_mode  # Always enabled in coding mode
    )


# MCP API Routes
@app.route('/mcps', methods=['GET'])
def mcps_web_interface():
    """Web interface for MCP management"""
    return render_template('mcps.html')


@app.route('/mcps/<mcp_id>', methods=['GET'])
def mcp_details_page(mcp_id):
    """Web interface for MCP details"""
    return render_template('mcp_details.html', mcp_id=mcp_id)


@app.route('/api/mcps', methods=['GET'])
def api_list_mcps():
    """List all registered MCPs"""
    try:
        mcps = get_all_mcps_from_redis()
        is_coding_mode = get_coding_mode_status()

        # Format MCPs for response
        formatted_mcps = []
        for mcp in mcps:
            formatted_mcp = {
                'id': mcp.get('id'),
                'name': mcp.get('name'),
                'description': mcp.get('description'),
                'tools_count': int(mcp.get('tools_count', 0)),
                'resources_count': int(mcp.get('resources_count', 0)),
                'enabled': mcp.get('enabled') == 'true',
                'always_enabled': mcp.get('always_enabled') == 'true',
                'can_toggle': mcp.get('always_enabled') != 'true',
                'registered_at': mcp.get('registered_at')
            }
            formatted_mcps.append(formatted_mcp)

        return jsonify({
            'success': True,
            'mcps': formatted_mcps,
            'coding_mode': is_coding_mode,
            'count': len(formatted_mcps)
        })
    except Exception as e:
        error_handler.handle_exception(e, context={'operation': 'api_list_mcps'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mcps/<mcp_id>/toggle', methods=['POST'])
def api_toggle_mcp(mcp_id):
    """Toggle MCP enabled/disabled status"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)

        result = toggle_mcp_enabled(mcp_id, enabled)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        error_handler.handle_exception(e, context={'operation': 'api_toggle_mcp', 'mcp_id': mcp_id})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mcps/<mcp_id>', methods=['GET'])
def api_get_mcp_details(mcp_id):
    """Get detailed information about an MCP including tools and resources"""
    try:
        if not redis_client:
            return jsonify({'success': False, 'error': 'Redis not available'}), 500

        mcp_key = f'mcp:{mcp_id}'
        if not redis_client.exists(mcp_key):
            return jsonify({'success': False, 'error': 'MCP not found'}), 404

        mcp_data = redis_client.hgetall(mcp_key)

        # For mirror-vanisher-dev, provide actual tool list
        tools = []
        resources = []

        if mcp_id == 'mirror-vanisher-dev':
            tools = [
                {'name': 'list_mirror_vanishers', 'description': 'List all mirror+vanisher directories'},
                {'name': 'verify_mirror_vanisher', 'description': 'Verify a path is a valid mirror+vanisher'},
                {'name': 'explore_structure', 'description': 'Generate directory tree'},
                {'name': 'detect_tech_stack', 'description': 'Identify languages and frameworks'},
                {'name': 'find_entrypoints', 'description': 'Locate main executable files'},
                {'name': 'full_exploration', 'description': 'Combined exploration tool'},
                {'name': 'analyze_architecture', 'description': 'Identify architectural patterns'},
                {'name': 'map_dependencies', 'description': 'Map imports and dependencies'},
                {'name': 'identify_patterns', 'description': 'Find design patterns'},
                {'name': 'chunk_file', 'description': 'Break a file into chunks'},
                {'name': 'chunk_directory', 'description': 'Create chunking strategy for directory'},
                {'name': 'create_plan', 'description': 'Generate implementation plan'},
                {'name': 'run_tests', 'description': 'Execute tests'},
                {'name': 'full_quality_check', 'description': 'Run linter, formatter, and type checker'},
                {'name': 'scan_secrets', 'description': 'Find hardcoded secrets'},
                {'name': 'security_audit', 'description': 'Complete security audit'},
                {'name': 'complete_feature_workflow', 'description': 'End-to-end feature implementation'},
                {'name': 'bugfix_workflow', 'description': 'Systematic bug fixing'}
            ]

        return jsonify({
            'success': True,
            'mcp': {
                'id': mcp_data.get('id'),
                'name': mcp_data.get('name'),
                'description': mcp_data.get('description'),
                'tools_count': int(mcp_data.get('tools_count', 0)),
                'resources_count': int(mcp_data.get('resources_count', 0)),
                'enabled': mcp_data.get('enabled') == 'true',
                'always_enabled': mcp_data.get('always_enabled') == 'true',
                'registered_at': mcp_data.get('registered_at'),
                'tools': tools,
                'resources': resources
            }
        })
    except Exception as e:
        error_handler.handle_exception(e, context={'operation': 'api_get_mcp_details', 'mcp_id': mcp_id})
        return jsonify({'success': False, 'error': str(e)}), 500


# Start background sync monitor thread
if redis_client:
    sync_monitor_thread = Thread(target=mirror_sync_monitor, daemon=True)
    sync_monitor_thread.start()
    logger.info("Started background mirror sync monitor")
else:
    logger.info("Redis not available, sync monitor disabled")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

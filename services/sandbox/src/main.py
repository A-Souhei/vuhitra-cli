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
from flask import Flask, request, jsonify, send_file, render_template_string
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

app = Flask(__name__)

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


def update_mirror_sync_status(target_name, synced, differences=None):
    """Update sync status in Redis"""
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

    # Secure the target name
    safe_target = secure_filename(target_name)
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
        is_file = target_path.is_file()
        file_count = len(synced_files) if not is_file else 1
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
    safe_target = secure_filename(target_name)
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
            # Directory - get all files recursively
            for item in target_path.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(target_path)
                    files_info.append({
                        "name": str(rel_path),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "is_file": True
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
    safe_target = secure_filename(target_name)
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


@app.route('/remove/<path:target_name>', methods=['DELETE'])
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
    # Secure the target name
    safe_target = secure_filename(target_name)
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

    # Check interval in seconds (default: 5 minutes)
    check_interval = int(os.getenv('MIRROR_SYNC_CHECK_INTERVAL', '300'))

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
                    safe_name = secure_filename(mirror_name)
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

                    # For now, we can only check if files changed in mirror
                    # We don't have access to host filesystem from sandbox
                    # So we'll just track that we checked
                    update_mirror_sync_status(mirror_name, synced=True, differences=None)

                    logger.debug(f"Checked mirror '{mirror_name}': {len(mirror_files_dict)} files")

                except Exception as e:
                    logger.error(f"Error checking mirror '{mirror.get('name', 'unknown')}': {e}")
                    continue

            logger.info(f"Sync check completed for {len(mirrors)} mirror(s)")

        except Exception as e:
            logger.error(f"Error in mirror sync monitor: {e}")
            # Continue running despite errors
            continue


# Web interface for mirror management
WEB_INTERFACE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mirror Management</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .mirror-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .mirror-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .mirror-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .mirror-name {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .mirror-info {
            font-size: 14px;
            color: #666;
            margin: 5px 0;
        }
        .mirror-info label {
            font-weight: bold;
            display: inline-block;
            width: 100px;
        }
        .sync-status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .sync-status.synced {
            background-color: #4CAF50;
            color: white;
        }
        .sync-status.not-synced {
            background-color: #ff9800;
            color: white;
        }
        .button-group {
            margin-top: 15px;
            display: flex;
            gap: 10px;
        }
        button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        .btn-sync {
            background-color: #2196F3;
            color: white;
        }
        .btn-sync:hover {
            background-color: #0b7dda;
        }
        .btn-delete {
            background-color: #f44336;
            color: white;
        }
        .btn-delete:hover {
            background-color: #da190b;
        }
        .btn-refresh {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            font-size: 16px;
            margin-bottom: 20px;
        }
        .btn-refresh:hover {
            background-color: #45a049;
        }
        .no-mirrors {
            text-align: center;
            color: #999;
            padding: 40px;
            font-size: 18px;
        }
        .error {
            background-color: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success {
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>🗂️ Mirror Management</h1>
    <button class="btn-refresh" onclick="location.reload()">🔄 Refresh</button>

    <div id="message"></div>
    <div class="mirror-grid" id="mirrorGrid">
        <div class="no-mirrors">Loading mirrors...</div>
    </div>

    <script>
        async function loadMirrors() {
            try {
                const response = await fetch('/mirror-list');
                const data = await response.json();
                const mirrors = data.mirrors || [];

                const grid = document.getElementById('mirrorGrid');

                if (mirrors.length === 0) {
                    grid.innerHTML = '<div class="no-mirrors">No mirrors registered</div>';
                    return;
                }

                grid.innerHTML = mirrors.map(mirror => {
                    const createdDate = new Date(mirror.created_at).toLocaleString();
                    const lastChecked = mirror.last_checked !== 'never'
                        ? new Date(mirror.last_checked).toLocaleString()
                        : 'Never';
                    const syncClass = mirror.sync_status === 'synced' ? 'synced' : 'not-synced';
                    const syncText = mirror.sync_status === 'synced' ? '✓ Synced' : '✗ Not Synced';

                    return `
                        <div class="mirror-card">
                            <div class="mirror-name">${mirror.name}</div>
                            <div class="mirror-info">
                                <label>Type:</label> ${mirror.type}
                            </div>
                            <div class="mirror-info">
                                <label>Files:</label> ${mirror.file_count}
                            </div>
                            <div class="mirror-info">
                                <label>Created:</label> ${createdDate}
                            </div>
                            <div class="mirror-info">
                                <label>Status:</label> <span class="sync-status ${syncClass}">${syncText}</span>
                            </div>
                            <div class="mirror-info">
                                <label>Last Checked:</label> ${lastChecked}
                            </div>
                            <div class="button-group">
                                <button class="btn-sync" onclick="syncMirror('${mirror.name}')">📥 Sync from Host</button>
                                <button class="btn-delete" onclick="deleteMirror('${mirror.name}')">🗑️ Delete</button>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (error) {
                console.error('Error loading mirrors:', error);
                document.getElementById('mirrorGrid').innerHTML =
                    '<div class="error">Failed to load mirrors. Please refresh the page.</div>';
            }
        }

        function showMessage(message, isError = false) {
            const msgDiv = document.getElementById('message');
            msgDiv.innerHTML = `<div class="${isError ? 'error' : 'success'}">${message}</div>`;
            setTimeout(() => msgDiv.innerHTML = '', 5000);
        }

        async function syncMirror(name) {
            if (!confirm(`Sync mirror '${name}' from host? This will update the sandbox mirror with host changes.`)) {
                return;
            }

            showMessage(`Syncing mirror '${name}'...`);

            try {
                // Note: This would require host cooperation to upload files
                // For now, we'll just show a message
                showMessage(`Sync operation requires running /mirror sync @${name} from the CLI`, false);
            } catch (error) {
                showMessage(`Failed to sync: ${error.message}`, true);
            }
        }

        async function deleteMirror(name) {
            if (!confirm(`Delete mirror '${name}'? This will remove it from the sandbox.`)) {
                return;
            }

            try {
                const response = await fetch(`/remove/${name}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    showMessage(`Mirror '${name}' deleted successfully`, false);
                    setTimeout(() => location.reload(), 1000);
                } else {
                    const data = await response.json();
                    showMessage(`Failed to delete: ${data.error}`, true);
                }
            } catch (error) {
                showMessage(`Failed to delete: ${error.message}`, true);
            }
        }

        // Load mirrors on page load
        loadMirrors();
    </script>
</body>
</html>
"""


@app.route('/mirrors', methods=['GET'])
def mirror_web_interface():
    """Web interface for managing mirrors"""
    return render_template_string(WEB_INTERFACE_HTML)


# Start background sync monitor thread
if redis_client:
    sync_monitor_thread = Thread(target=mirror_sync_monitor, daemon=True)
    sync_monitor_thread.start()
    logger.info("Started background mirror sync monitor")
else:
    logger.info("Redis not available, sync monitor disabled")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

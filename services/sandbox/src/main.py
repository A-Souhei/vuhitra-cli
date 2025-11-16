import shutil
import sys
import os
import logging
import io
import zipfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

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
            for file_path in target_path.rglob('*'):
                if file_path.is_file():
                    # Get path relative to the mirror directory
                    arcname = file_path.relative_to(target_path)
                    zf.write(file_path, arcname=str(arcname))

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

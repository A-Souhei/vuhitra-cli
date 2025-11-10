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

# Configuration
WORKSPACE_DIR = Path("/app/WORKSPACE")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size


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
    return jsonify({
        "status": "healthy", 
        "service": "sandbox",
        "heuristics": health_status
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
    Expects JSON: {prompt, response, rating, timestamp, execution_time_ms}
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['prompt', 'response', 'rating', 'timestamp']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        result = heuristics.process_feedback(data)
        return jsonify(result), 202  # 202 Accepted (async processing)
        
    except Exception as e:
        raise SandboxException("Failed to process feedback", 
                             operation="analyze_feedback") from e


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

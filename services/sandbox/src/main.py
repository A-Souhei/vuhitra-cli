import shutil
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WORKSPACE_DIR = Path("/app/WORKSPACE")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "sandbox"}), 200


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
        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "path": str(filepath)
        }), 200
    except Exception as e:
        logger.error(f"Failed to upload file {filename}: {str(e)}")
        return jsonify({"error": "Failed to upload file"}), 500


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
            logger.error(f"Failed to upload file {filename}: {str(e)}")
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
    except Exception:
        return jsonify({"error": "Invalid file path"}), 400
    
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    
    try:
        if filepath.is_file():
            filepath.unlink()
            return jsonify({
                "message": "File removed successfully",
                "filename": safe_filename
            }), 200
        else:
            return jsonify({"error": "Not a file"}), 400
    except Exception as e:
        logger.error(f"Failed to remove file {safe_filename}: {str(e)}")
        return jsonify({"error": "Failed to remove file"}), 500


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
        
        return jsonify({
            "message": "All files removed successfully",
            "removed_count": removed_count
        }), 200
    except Exception as e:
        logger.error(f"Failed to remove all files: {str(e)}")
        return jsonify({"error": "Failed to remove all files"}), 500


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
        
        return jsonify({
            "workspace": str(WORKSPACE_DIR),
            "file_count": len(files),
            "files": files
        }), 200
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        return jsonify({"error": "Failed to list files"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

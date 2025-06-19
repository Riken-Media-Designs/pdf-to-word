import os
import tempfile
import uuid
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pdf2docx import Converter
import logging

conversion_bp = Blueprint('conversion', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= MAX_FILE_SIZE

@conversion_bp.route('/convert', methods=['POST'])
def convert_pdf():
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
        
        # Validate file size
        if not validate_file_size(file):
            return jsonify({'error': 'File size exceeds 50MB limit'}), 400
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            file.save(temp_pdf.name)
            temp_pdf_path = temp_pdf.name
        
        # Generate output filename
        original_filename = secure_filename(file.filename)
        base_name = os.path.splitext(original_filename)[0]
        output_filename = f"{base_name}.docx"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_docx:
            temp_docx_path = temp_docx.name
        
        try:
            # Convert PDF to Word using pdf2docx
            logger.info(f"Starting conversion of {original_filename}")
            cv = Converter(temp_pdf_path)
            cv.convert(temp_docx_path, start=0, end=None)
            cv.close()
            logger.info(f"Conversion completed for {original_filename}")
            
            # Return the converted file
            return send_file(
                temp_docx_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                if os.path.exists(temp_docx_path):
                    os.unlink(temp_docx_path)
            except Exception as cleanup_error:
                logger.warning(f"Cleanup error: {str(cleanup_error)}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@conversion_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'PDF conversion service is running',
        'engine': 'pdf2docx'
    })


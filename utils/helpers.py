import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request, redirect, url_for, flash, jsonify
from flask_login import current_user

def login_required_api(f):
    """API route decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'redirect': url_for('auth.login')
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Route decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
            
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def format_datetime(value, format='medium'):
    """Jinja2 filter to format datetime objects."""
    if not value:
        return ""
        
    if format == 'full':
        format = "%A, %B %d, %Y at %I:%M %p"
    elif format == 'medium':
        format = "%b %d, %Y %I:%M %p"
    elif format == 'date':
        format = "%Y-%m-%d"
    elif format == 'time':
        format = "%I:%M %p"
        
    return value.strftime(format)

def humanize_timedelta(delta):
    """Convert a timedelta into a human-readable string."""
    if not isinstance(delta, timedelta):
        return ""
        
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def get_file_extension(filename):
    """Get the file extension from a filename."""
    if not filename:
        return ""
    return os.path.splitext(filename)[1].lower()

def allowed_file(filename, allowed_extensions):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           get_file_extension(filename) in allowed_extensions

def save_uploaded_file(file, upload_folder, allowed_extensions=None):
    """Save an uploaded file to the specified folder."""
    if not file or file.filename == '':
        return None
        
    if allowed_extensions and not allowed_file(file.filename, allowed_extensions):
        return None
        
    # Create a secure filename
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    
    # Ensure the upload folder exists
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save the file
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    return filepath

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def to_json(data):
    """Convert data to JSON string."""
    return json.dumps(data, default=json_serial)

def from_json(json_str):
    """Convert JSON string to Python object."""
    return json.loads(json_str) if json_str else None

def get_pagination(page, per_page=10):
    """Get pagination parameters."""
    try:
        page = int(page)
        if page < 1:
            page = 1
    except (TypeError, ValueError):
        page = 1
        
    return {
        'page': page,
        'per_page': per_page,
        'offset': (page - 1) * per_page
    }

def get_client_ip():
    """Get the client's IP address."""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    else:
        return request.remote_addr

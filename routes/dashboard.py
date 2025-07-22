from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models.journal import JournalEntry
from models.repository import Repository

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Get recent journal entries
    recent_entries = JournalEntry.query\
        .filter_by(user_id=current_user.id)\
        .order_by(JournalEntry.created_at.desc())\
        .limit(3)\
        .all()
    
    # Get recent repositories
    recent_repos = Repository.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Repository.created_at.desc())\
        .limit(3)\
        .all()
    
    # Get statistics (example - you can expand this)
    stats = {
        'total_journals': JournalEntry.query.filter_by(user_id=current_user.id).count(),
        'total_repos': Repository.query.filter_by(user_id=current_user.id).count(),
        'recent_activity': []  # You can add recent activity here
    }
    
    return render_template(
        'dashboard.html',
        recent_entries=recent_entries,
        recent_repos=recent_repos,
        stats=stats
    )

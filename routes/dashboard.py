from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models.journal import JournalEntry
from models.repository import Repository
from datetime import datetime, timedelta
import json

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
    
    # Get repository analysis data
    repos = Repository.query.filter_by(user_id=current_user.id).all()
    
    # Calculate repository metrics
    total_commits = sum(repo.total_commits or 0 for repo in repos)
    total_authors = sum(repo.total_authors or 0 for repo in repos)
    
    # Get repositories with burnout risk (top 3)
    risky_repos = sorted(
        [r for r in repos if r.burnout_risk and r.burnout_risk > 0.5],
        key=lambda x: x.burnout_risk,
        reverse=True
    )[:3]
    
    # Get recent activity from repositories (commits in the last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = []
    
    for repo in repos:
        if repo.last_commit_date and repo.last_commit_date >= week_ago:
            recent_activity.append({
                'type': 'commit',
                'repo': repo.name,
                'timestamp': repo.last_commit_date,
                'message': f"New commits in {repo.name}"
            })
    
    # Sort by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get statistics
    stats = {
        'total_journals': JournalEntry.query.filter_by(user_id=current_user.id).count(),
        'total_repos': len(repos),
        'total_commits': total_commits,
        'total_authors': total_authors,
        'recent_activity': recent_activity[:5],
        'risky_repos': [{
            'id': r.id,
            'name': r.name,
            'risk_score': round((r.burnout_risk or 0) * 100, 1),
            'last_analyzed': r.last_analyzed.strftime('%Y-%m-%d') if r.last_analyzed else 'Never'
        } for r in risky_repos]
    }
    
    return render_template(
        'dashboard.html',
        recent_entries=recent_entries,
        recent_repos=recent_repos,
        stats=stats
    )

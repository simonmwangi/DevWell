from flask import Blueprint, render_template, jsonify, current_app, request
from flask_login import login_required, current_user
from models.journal import JournalEntry
from models.repository import Repository, Commit
from models.wellness_snapshot import WellnessSnapshot
from datetime import datetime, timedelta
from sqlalchemy import func
import json
import os

# Import WellnessRecommender
from ai_services.wellness_recommender import WellnessRecommender

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
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
    
    # Get journal sentiment data for wellness analysis
    journal_sentiment = JournalEntry.query.with_entities(
        func.avg(JournalEntry.sentiment_score).label('avg_sentiment'),
        func.count(JournalEntry.id).label('entry_count')
    ).filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.created_at >= (datetime.utcnow() - timedelta(days=30))
    ).first()

    # Initialize WellnessRecommender
    model_path = os.path.join(current_app.root_path, 'models', 'wellness_model.joblib')

    print(model_path)
    recommender = WellnessRecommender(model_path if os.path.exists(model_path) else None)
    
    # Prepare git data for analysis (last 30 days)
    lookback_days = 30
    since_date = datetime.utcnow() - timedelta(days=lookback_days)

    commits = (Commit.query
               .join(Repository)
               .filter(Repository.user_id == current_user.id,
                       Commit.timestamp >= since_date)
               .all())

    total_commits = len(commits)

    # Early-exit defaults when no commits are found
    if not commits:
        git_data = {
            'weekly_hours': 0,
            'avg_daily_commits': 0,
            'schedule_regularity': 0,
            'collaboration_score': 0,
            'late_night_commits': 0,
            'weekend_commit_ratio': 0,
            'max_commit_streak_hours': 0,
        }
    else:
        from collections import defaultdict
        from statistics import variance

        daily_counts = defaultdict(int)
        distinct_hours = set()
        late_night = 0
        weekend = 0
        authors = set()

        timestamps = []

        for c in commits:
            ts = c.timestamp
            timestamps.append(ts)
            authors.add(c.author)

            daily_counts[ts.date()] += 1
            distinct_hours.add((ts.date(), ts.hour))

            if ts.hour >= 22 or ts.hour < 4:
                late_night += 1
            if ts.weekday() >= 5:
                weekend += 1

        # Metrics calculations
        avg_daily_commits = total_commits / lookback_days

        if len(daily_counts) > 1:
            schedule_var = variance(daily_counts.values())
            schedule_regularity = max(0.0, 1.0 - min(schedule_var / 10.0, 1.0))  # Normalize
        else:
            schedule_regularity = 1.0

        collaboration_score = max(0.0, (len(authors) - 1) / len(authors)) if authors else 0.0

        weekend_commit_ratio = weekend / total_commits if total_commits else 0.0

        weekly_hours = (len(distinct_hours) / lookback_days) * 7

        # Longest streak where consecutive commits are within 1-hour gaps
        timestamps.sort()
        max_streak_hours = 0.0
        streak_start = timestamps[0]
        for i in range(1, len(timestamps)):
            diff_hours = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600.0
            if diff_hours <= 1:
                # extend streak
                continue
            else:
                streak_length = (timestamps[i - 1] - streak_start).total_seconds() / 3600.0
                max_streak_hours = max(max_streak_hours, streak_length)
                streak_start = timestamps[i]
        # Final streak from last segment
        final_streak = (timestamps[-1] - streak_start).total_seconds() / 3600.0
        max_streak_hours = max(max_streak_hours, final_streak)

        git_data = {
            'weekly_hours': round(weekly_hours, 1),
            'avg_daily_commits': round(avg_daily_commits, 2),
            'schedule_regularity': round(schedule_regularity, 2),
            'collaboration_score': round(collaboration_score, 2),
            'late_night_commits': late_night,
            'weekend_commit_ratio': round(weekend_commit_ratio, 2),
            'max_commit_streak_hours': round(max_streak_hours, 1),
        }
    
    # Prepare journal data for analysis
    journal_data = {
        'avg_sentiment': float(journal_sentiment.avg_sentiment) if journal_sentiment and journal_sentiment.avg_sentiment is not None else 0,
        'entry_count': journal_sentiment.entry_count if journal_sentiment else 0,
        'days_since_last_journal': (datetime.utcnow() - 
            JournalEntry.query.filter_by(user_id=current_user.id)
            .order_by(JournalEntry.created_at.desc())
            .first().created_at).days if JournalEntry.query.filter_by(user_id=current_user.id).first() else 999
    }
    
    # Generate wellness recommendations
    wellness_tips = recommender.generate_daily_tips({
        **git_data,
        **journal_data,
        'hours_since_last_break': 2,  # Should be calculated from activity data
        'work_life_balance_score': 0.6  # Should be calculated from work patterns
    })
    
    # Analyze burnout risk
    burnout_analysis = recommender.analyze_burnout_risk(git_data, journal_data)
    
    # Get work-life balance tips
    work_life_tips = recommender.get_work_life_balance_tips(git_data)
    
    # Calculate wellness score (0-10 scale)
    wellness_score = max(0, min(10, 8 - (burnout_analysis['risk_score'] * 5)))
    
    # Persist / update today's wellness snapshot
    today = datetime.utcnow().date()
    snap = WellnessSnapshot.query.filter_by(user_id=current_user.id, snapshot_date=today).first()
    if not snap:
        snap = WellnessSnapshot(user_id=current_user.id, snapshot_date=today)

    # update fields
    snap.weekly_hours = git_data['weekly_hours']
    snap.avg_daily_commits = git_data['avg_daily_commits']
    snap.schedule_regularity = git_data['schedule_regularity']
    snap.collaboration_score = git_data['collaboration_score']
    snap.late_night_commits = git_data['late_night_commits']
    snap.weekend_commit_ratio = git_data['weekend_commit_ratio']
    snap.max_commit_streak_hours = git_data['max_commit_streak_hours']

    snap.avg_sentiment = journal_data['avg_sentiment']
    snap.entry_count = journal_data['entry_count']
    snap.days_since_last_journal = journal_data['days_since_last_journal']

    snap.wellness_score = wellness_score
    snap.burnout_risk = burnout_analysis['risk_score'] if isinstance(burnout_analysis, dict) else 0

    from extensions import db
    db.session.add(snap)
    db.session.commit()

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
        } for r in risky_repos],
        'wellness': {
            'score': round(wellness_score, 1),
            'level': 'Excellent' if wellness_score >= 8 else 'Good' if wellness_score >= 6 else 'Needs Attention',
            'trend': 'up' if wellness_score >= 7 else 'down' if wellness_score <= 5 else 'stable',
            'burnout_risk': burnout_analysis,
            'tips': wellness_tips,
            'work_life_tips': work_life_tips
        }
    }
    
    return render_template(
        'dashboard.html',
        recent_entries=recent_entries,
        recent_repos=recent_repos,
        stats=stats
    )

@dashboard_bp.route('/wellness-resources')
@login_required
def wellness_resources():
    """
    Render the wellness resources page with resources filtered by category.
    """
    category = request.args.get('category', '').lower()
    
    # Define wellness resources by category
    resources = {
        'stress_relief': [
            {
                'title': '5-Minute Breathing Exercise',
                'description': 'A quick guided breathing exercise to reduce stress and anxiety.',
                'url': 'https://www.healthline.com/health/breathing-exercise',
                'duration': '5 min'
            },
            {
                'title': 'Progressive Muscle Relaxation',
                'description': 'Step-by-step guide to releasing tension throughout your body.',
                'url': 'https://www.healthline.com/health/progressive-muscle-relaxation',
                'duration': '10 min'
            }
        ],
        'sleep': [
            {
                'title': 'Sleep Hygiene Tips',
                'description': 'Best practices for improving your sleep quality.',
                'url': 'https://www.sleepfoundation.org/sleep-hygiene',
                'duration': '5 min read'
            },
            {
                'title': 'Guided Sleep Meditation',
                'description': 'A calming meditation to help you fall asleep faster.',
                'url': 'https://www.headspace.com/sleep',
                'duration': '15 min'
            }
        ],
        'productivity': [
            {
                'title': 'Pomodoro Technique',
                'description': 'A time management method to boost productivity.',
                'url': 'https://todoist.com/productivity-methods/pomodoro-technique',
                'duration': '5 min read'
            },
            {
                'title': 'Time Blocking Guide',
                'description': 'How to organize your day for maximum efficiency.',
                'url': 'https://www.calendar.com/blog/time-blocking/',
                'duration': '8 min read'
            }
        ],
        'breaks': [
            {
                'title': 'Desk Stretches',
                'description': 'Simple stretches you can do at your desk to prevent stiffness.',
                'url': 'https://www.healthline.com/health/desk-stretches',
                'duration': '5 min'
            },
            {
                'title': '20-20-20 Rule',
                'description': 'Prevent eye strain with this simple technique.',
                'url': 'https://www.healthline.com/health/eye-health/20-20-20-rule',
                'duration': '1 min read'
            }
        ]
    }
    
    # Get all categories for the filter
    all_categories = [
        ('stress_relief', 'Stress Relief'),
        ('sleep', 'Sleep'),
        ('productivity', 'Productivity'),
        ('breaks', 'Breaks')
    ]
    
    # Filter resources by category if specified
    filtered_resources = resources.get(category, [])
    
    # If no category is specified, show all resources
    if not category:
        filtered_resources = [resource for category_resources in resources.values() for resource in category_resources]
    
    return render_template(
        'wellness_resources.html',
        resources=filtered_resources,
        categories=all_categories,
        current_category=category
    )

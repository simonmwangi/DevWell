import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from models.repository import Repository, Commit
from extensions import db
from forms import RepositoryForm
from ai_services.git_analyzer import GitAnalyzer
import git
from datetime import datetime, timedelta
import json

# Create blueprint
repo_bp = Blueprint('repository', __name__)

@repo_bp.route('/')
@login_required
def index():
    repositories = Repository.query.filter_by(user_id=current_user.id).all()
    return render_template('repository_list.html', repositories=repositories)

@repo_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_repository():
    form = RepositoryForm(current_user = current_user)
    
    if form.validate_on_submit():
        try:
            # Create local path for the repository
            local_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                str(current_user.id),
                form.name.data.lower().replace(' ', '_')
            )
            
            # Clone the repository
            repo = git.Repo.clone_from(form.repo_url.data, local_path)

            last_commit = repo.head.commit
            last_commit_date = last_commit.committed_datetime 
            
            # Create repository record
            repository = Repository(
                name=form.name.data,
                repo_url=form.repo_url.data,
                description=form.description.data,
                local_path=local_path,
                user_id=current_user.id,
                last_commit_date=last_commit_date
            )
            
            db.session.add(repository)
            db.session.commit()
            
            # Analyze commits
            analyze_repository_commits(repository.id, repo)
            
            flash('Repository added and analyzed successfully!', 'success')
            return redirect(url_for('repository.view_repository', repo_id=repository.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding repository: {str(e)}', 'danger')
            # Clean up if there was an error
            if 'local_path' in locals() and os.path.exists(local_path):
                import shutil
                shutil.rmtree(local_path, ignore_errors=True)
    
    return render_template('repository_form.html', form=form)

@repo_bp.route('/<int:repo_id>')
@login_required
def view_repository(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repository.user_id != current_user.id:
        flash('You do not have permission to view this repository', 'danger')
        return redirect(url_for('repository.index'))
    
    # Get recent commits
    recent_commits = Commit.query\
        .filter_by(repository_id=repository.id)\
        .order_by(Commit.timestamp.desc())\
        .limit(10)\
        .all()
    
    # Get commit statistics
    commit_stats = {
        'total_commits': Commit.query.filter_by(repository_id=repository.id).count(),
        'total_lines_added': db.session.query(db.func.sum(Commit.lines_added))\
            .filter_by(repository_id=repository.id).scalar() or 0,
        'total_lines_removed': db.session.query(db.func.sum(Commit.lines_removed))\
            .filter_by(repository_id=repository.id).scalar() or 0,
    }
    
    # Get analysis data if available
    analysis_data = {}
    if repository.analysis_summary:
        try:
            analysis_data = json.loads(repository.analysis_summary)
        except (json.JSONDecodeError, AttributeError):
            current_app.logger.warning(f'Invalid analysis data for repository {repository.id}')
    
    # Prepare data for charts
    chart_data = {}
    if 'commit_patterns' in analysis_data:
        # Prepare commit frequency chart data
        hour_dist = analysis_data['commit_patterns'].get('commit_hour_distribution', {})
        chart_data['commit_hours'] = [hour_dist.get(str(h), 0) for h in range(24)]
        
        day_dist = analysis_data['commit_patterns'].get('commit_day_distribution', {})
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        chart_data['commit_days'] = [day_dist.get(str(i), 0) for i in range(7)]
        chart_data['day_labels'] = days
    
    if 'sentiment_analysis' in analysis_data:
        sentiment = analysis_data['sentiment_analysis']
        chart_data['sentiment_data'] = {
            'positive': sentiment.get('positive_commits_ratio', 0) * 100,
            'negative': sentiment.get('negative_commits_ratio', 0) * 100,
            'neutral': (1 - (sentiment.get('positive_commits_ratio', 0) + 
                           sentiment.get('negative_commits_ratio', 0))) * 100
        }
    
    if 'burnout_indicators' in analysis_data:
        burnout = analysis_data['burnout_indicators']
        chart_data['burnout_metrics'] = {
            'late_night': burnout.get('late_night_commits', 0),
            'weekend': burnout.get('weekend_commits', 0),
            'message_quality': burnout.get('message_quality_score', 0) * 100,
            'recent_frequency': round(burnout.get('recent_commit_frequency', 0), 1),
            'risk_score': (burnout.get('burnout_risk', 0) * 100) if 'burnout_risk' in burnout else 0
        }
    
    now = datetime.utcnow()
    
    # Prepare wellness recommendation data
    wellness_context = {
        'commit_hour_avg': analysis_data.get('commit_patterns', {}).get('average_commit_hour', 12),  # Default to noon if not available
        'commit_frequency': analysis_data.get('commit_patterns', {}).get('commit_frequency', 0),
        'last_commit_days_ago': (now - (repository.last_commit_date or now)).days
    }

    return render_template(
        'repository_view.html',
        repository=repository,
        recent_commits=recent_commits,
        stats=commit_stats,
        analysis=analysis_data,
        chart_data=chart_data,
        Commit=Commit,
        form=RepositoryForm(current_user=current_user),
        last_analyzed=repository.last_analyzed,
        now=now,
        wellness_context=wellness_context
    )

def analyze_repository_commits(repo_id, git_repo):
    """Analyze commits for a repository and store them in the database."""
    try:
        # Get existing commit hashes to avoid duplicates
        existing_hashes = {c.commit_hash for c in Commit.query.filter_by(repository_id=repo_id).all()}
        
        # Process new commits
        for commit in git_repo.iter_commits():
            if commit.hexsha in existing_hashes:
                continue
                
            # Count added and removed lines
            stats = commit.stats.total
            
            # Create commit record
            db_commit = Commit(
                commit_hash=commit.hexsha,
                author=f"{commit.author.name} <{commit.author.email}>",
                message=commit.message,
                timestamp=datetime.fromtimestamp(commit.committed_date),
                lines_added=stats.get('insertions', 0),
                lines_removed=stats.get('deletions', 0),
                repository_id=repo_id
            )
            
            db.session.add(db_commit)
        
        # Update last analyzed timestamp
        repository = Repository.query.get(repo_id)
        repository.last_analyzed = datetime.utcnow()
        
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing repository commits: {str(e)}")
        db.session.rollback()
        raise

@repo_bp.route('/<int:repo_id>/refresh', methods=['POST'])
@login_required
def refresh_repository(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repository.user_id != current_user.id:
        flash('You do not have permission to refresh this repository', 'danger')
        return redirect(url_for('repository.index'))
        
    try:
        # Pull the latest changes
        repo = git.Repo(repository.local_path)
        origin = repo.remotes.origin
        origin.pull()
        
        # Update the repository record
        repository.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Re-analyze commits
        analyze_repository_commits(repository.id, repo)
        
        flash('Repository refreshed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error refreshing repository: {str(e)}', 'danger')
    
    print("Repository refreshed successfully!") 
    return redirect(url_for('repository.view_repository', repo_id=repository.id))

@repo_bp.route('/<int:repo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_repository(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repository.user_id != current_user.id:
        flash('You do not have permission to edit this repository', 'danger')
        return redirect(url_for('repository.index'))
    
    form = RepositoryForm()
    
    if form.validate_on_submit():
        try:
            repository.name = form.name.data
            repository.repo_url = form.repo_url.data
            repository.description = form.description.data
            
            db.session.commit()
            flash('Repository updated successfully!', 'success')
            return redirect(url_for('repository.view_repository', repo_id=repository.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating repository: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.name.data = repository.name
        form.repo_url.data = repository.repo_url
        form.description.data = repository.description
        form.repo_id.data = repository.id
    
    return render_template('repository_form.html', form=form, repository=repository)

@repo_bp.route('/delete/<int:repo_id>', methods=['POST'])
@login_required
def delete_repository(repo_id):
    repo = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repo.user_id != current_user.id:
        flash('You do not have permission to delete this repository', 'danger')
        return redirect(url_for('repository.index'))
    
    try:
        # Delete the repository directory
        if os.path.exists(repo.local_path):
            import shutil
            shutil.rmtree(repo.local_path)
        
        # Delete from database
        db.session.delete(repo)
        db.session.commit()
        
        flash('Repository deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting repository: {str(e)}')
        flash('An error occurred while deleting the repository', 'danger')
    
    return redirect(url_for('repository.index'))

@repo_bp.route('/<int:repo_id>/analyze', methods=['POST'])
@login_required
def analyze_repository(repo_id):
    """
    Analyze repository using GitAnalyzer and return detailed metrics.
    Updates the repository with analysis results for quick access.
    This endpoint is called via AJAX from the UI.
    """
    repo = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repo.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    try:
        # Check if the repository exists locally
        if not os.path.exists(repo.local_path):
            return jsonify({
                'status': 'error',
                'message': f'Repository not found at {repo.local_path}. Please refresh the repository first.'
            }), 404
            
        # Set analysis status to pending
        repo.last_analysis_status = 'pending'
        db.session.commit()
        
        # Initialize GitAnalyzer
        analyzer = GitAnalyzer()
        
        try:
            # Analyze repository (last 30 days by default)
            analysis = analyzer.analyze_repository(repo.local_path)
            
            if analysis:
                # Update repository with analysis results
                repo.analysis_summary = json.dumps(analysis)
                repo.last_analyzed = datetime.utcnow()
                repo.last_analysis_status = 'completed'
                
                # Update individual metrics for quick querying
                if 'commit_patterns' in analysis:
                    repo.total_commits = analysis['commit_patterns'].get('total_commits', 0)
                    repo.commit_frequency = analysis['commit_patterns'].get('commit_frequency', 0)
                    
                if 'sentiment_analysis' in analysis:
                    repo.avg_sentiment = analysis['sentiment_analysis'].get('avg_sentiment', 0)
                    
                if 'burnout_indicators' in analysis:
                    repo.burnout_risk = analysis['burnout_indicators'].get('burnout_risk', 0)
                
                if 'commit_patterns' in analysis and 'total_authors' in analysis['commit_patterns']:
                    repo.total_authors = analysis['commit_patterns']['total_authors']
                
                db.session.commit()
                
                # Return success response
                return jsonify({
                    'status': 'success',
                    'message': 'Analysis completed successfully',
                    'last_analyzed': repo.last_analyzed.strftime('%Y-%m-%d %H:%M:%S'),
                    'burnout_risk': getattr(repo, 'burnout_risk', 0) * 100  # Convert to percentage
                })
            else:
                raise Exception('No analysis results returned')
                
        except Exception as e:
            current_app.logger.error(f'Error during repository analysis: {str(e)}', exc_info=True)
            repo.last_analysis_status = 'failed'
            db.session.commit()
            return jsonify({
                'status': 'error',
                'message': f'Analysis failed: {str(e)}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f'Error in analyze_repository endpoint: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

@repo_bp.route('/<int:repo_id>/metrics')
@login_required
def get_repository_metrics(repo_id):
    """Get repository metrics for dashboard visualization."""
    repo = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repo.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Return cached analysis if available and recent (less than 1 hour old)
        if repo.analysis_summary and repo.last_analyzed and \
           (datetime.utcnow() - repo.last_analyzed) < timedelta(hours=1):
            return jsonify(json.loads(repo.analysis_summary))
        
        # Otherwise perform a fresh analysis
        return redirect(url_for('repository.analyze_repository', repo_id=repo_id))
    except Exception as e:
        current_app.logger.error(f'Error getting repository metrics: {str(e)}')
        return jsonify({'error': str(e)}), 500

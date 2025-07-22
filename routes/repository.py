import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models.repository import Repository, Commit
from extensions import db
from forms import RepositoryForm
import git
from datetime import datetime

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
    
    return render_template(
        'repository_view.html',
        repository=repository,
        recent_commits=recent_commits,
        stats=commit_stats,
        Commit=Commit,
        form=RepositoryForm(current_user=current_user)
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

@repo_bp.route('/<int:repo_id>/delete', methods=['POST'])
@login_required
def delete_repository(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    
    # Ensure the user owns this repository
    if repository.user_id != current_user.id:
        flash('You do not have permission to delete this repository', 'danger')
        return redirect(url_for('repository.index'))
    
    try:
        # Delete local repository
        if os.path.exists(repository.local_path):
            import shutil
            shutil.rmtree(repository.local_path)
        
        # Delete from database
        db.session.delete(repository)
        db.session.commit()
        
        flash('Repository deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting repository: {str(e)}', 'danger')
    
    return redirect(url_for('repository.index'))

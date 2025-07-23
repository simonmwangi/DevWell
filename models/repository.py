from datetime import datetime
from app import db

class Repository(db.Model):
    __tablename__ = 'repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    repo_url = db.Column(db.String(500), nullable=False)
    local_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_commit_date = db.Column(db.DateTime)
    
    # Analysis fields
    last_analyzed = db.Column(db.DateTime)
    analysis_summary = db.Column(db.Text)  # Stores JSON string of analysis results
    commit_frequency = db.Column(db.Float)  # Commits per day
    avg_sentiment = db.Column(db.Float)    # Average sentiment score (-1 to 1)
    burnout_risk = db.Column(db.Float)      # 0-1 scale
    total_commits = db.Column(db.Integer)   # Total number of commits
    total_authors = db.Column(db.Integer)   # Number of unique authors
    last_analysis_status = db.Column(db.String(20))  # 'pending', 'completed', 'failed'
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    commits = db.relationship('Commit', backref='repository', lazy='dynamic')
    
    def __init__(self, name, repo_url, user_id, description=None, local_path=None, last_commit_date=None):
        self.name = name
        self.repo_url = repo_url
        self.user_id = user_id
        self.description = description
        self.local_path = local_path
        self.last_commit_date = last_commit_date
    
    def __repr__(self):
        return f'<Repository {self.name}>'

class Commit(db.Model):
    __tablename__ = 'commits'
    
    id = db.Column(db.Integer, primary_key=True)
    commit_hash = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    lines_added = db.Column(db.Integer, default=0)
    lines_removed = db.Column(db.Integer, default=0)
    
    # Foreign Keys
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    
    def __init__(self, commit_hash, author, message, timestamp, repository_id, 
                 lines_added=0, lines_removed=0):
        self.commit_hash = commit_hash
        self.author = author
        self.message = message
        self.timestamp = timestamp
        self.repository_id = repository_id
        self.lines_added = lines_added
        self.lines_removed = lines_removed
    
    def __repr__(self):
        return f'<Commit {self.commit_hash[:7]}>'

from datetime import datetime
from app import db

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sentiment_score = db.Column(db.Float, default=0.0)
    sentiment_label = db.Column(db.String(20))
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __init__(self, title, content, user_id, sentiment_score=0.0, sentiment_label='neutral'):
        self.title = title
        self.content = content
        self.user_id = user_id
        self.sentiment_score = sentiment_score
        self.sentiment_label = sentiment_label
    
    def __repr__(self):
        return f'<JournalEntry {self.title}>'

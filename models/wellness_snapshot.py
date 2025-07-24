from datetime import date
from extensions import db

class WellnessSnapshot(db.Model):
    __tablename__ = 'wellness_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    snapshot_date = db.Column(db.Date, default=date.today, nullable=False, index=True)

    # Git metrics
    weekly_hours = db.Column(db.Float)
    avg_daily_commits = db.Column(db.Float)
    schedule_regularity = db.Column(db.Float)
    collaboration_score = db.Column(db.Float)
    late_night_commits = db.Column(db.Integer)
    weekend_commit_ratio = db.Column(db.Float)
    max_commit_streak_hours = db.Column(db.Float)

    # Journal metrics
    avg_sentiment = db.Column(db.Float)
    entry_count = db.Column(db.Integer)
    days_since_last_journal = db.Column(db.Integer)

    # Derived scores
    wellness_score = db.Column(db.Float)
    burnout_risk = db.Column(db.Float)

    def to_summary(self):
        return (
            f"Snapshot {self.snapshot_date} – wellness {self.wellness_score}, "
            f"burnout risk {self.burnout_risk}, avg sentiment {self.avg_sentiment}."
        )

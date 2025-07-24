"""Notification utilities for DevWell application."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from flask import current_app, render_template
from flask_mail import Message
from extensions import mail
from models.user import User
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages sending notifications to users."""
    
    @classmethod
    def send_email(
        cls,
        user: User,
        subject: str,
        template: str,
        **template_vars
    ) -> bool:
        """Send an email notification to the user.
        
        Args:
            user: The user to notify
            subject: Email subject
            template: Template name (without .html/.txt extension)
            **template_vars: Variables to pass to the template
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not user.email:
            logger.warning(f"User {user.id} has no email address configured")
            return False
            
        try:
            # Render both HTML and plain text versions
            html_body = render_template(f"emails/{template}.html", user=user, **template_vars)
            text_body = render_template(f"emails/{template}.txt", user=user, **template_vars)
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=html_body,
                body=text_body
            )
            
            mail.send(msg)
            logger.info(f"Email sent to {user.email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def send_daily_wellness_tips(cls, user: User) -> bool:
        """Send daily wellness tips to the user.
        
        Args:
            user: The user to send tips to
            
        Returns:
            bool: True if tips were sent successfully, False otherwise
        """
        from ai_services.wellness_recommender import WellnessRecommender
        
        try:
            # Get personalized tips
            recommender = WellnessRecommender()
            tips = recommender.generate_daily_tips({
                'user_id': user.id,
                'timezone': user.timezone or 'UTC'
            })
            
            if not tips:
                logger.warning(f"No wellness tips generated for user {user.id}")
                return False
                
            # Send email with tips
            return cls.send_email(
                user=user,
                subject="Your Daily Wellness Tips",
                template="daily_wellness_tips",
                tips=tips,
                date=datetime.utcnow().strftime("%A, %B %d, %Y")
            )
            
        except Exception as e:
            logger.error(f"Failed to send daily wellness tips to user {user.id}: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def send_burnout_alert(cls, user: User, risk_level: str, suggestions: List[Dict]) -> bool:
        """Send a burnout risk alert to the user.
        
        Args:
            user: The user to notify
            risk_level: One of 'low', 'moderate', 'high'
            suggestions: List of intervention suggestions
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        if risk_level == 'low':
            return False  # Don't send alerts for low risk
            
        try:
            return cls.send_email(
                user=user,
                subject=f"{risk_level.title()} Burnout Risk Detected",
                template="burnout_alert",
                risk_level=risk_level,
                suggestions=suggestions,
                date=datetime.utcnow().strftime("%A, %B %d, %Y")
            )
            
        except Exception as e:
            logger.error(f"Failed to send burnout alert to user {user.id}: {str(e)}", exc_info=True)
            return False


def schedule_wellness_notifications():
    """Schedule wellness notifications for all users.
    
    This should be called by a scheduled task (e.g., Celery beat or similar).
    """
    from models import db
    from sqlalchemy import func
    
    try:
        # Get users who want to receive notifications
        users = User.query.filter(
            User.email.isnot(None),
            User.email_verified.is_(True),
            User.notifications_enabled.is_(True)
        ).all()
        
        for user in users:
            # Check if we should send daily tips (once per day)
            last_tip = user.get_setting('last_daily_tip')
            if not last_tip or (datetime.utcnow() - last_tip).days >= 1:
                if NotificationManager.send_daily_wellness_tips(user):
                    user.set_setting('last_daily_tip', datetime.utcnow())
            
            # Check for burnout risk (if not checked today)
            last_check = user.get_setting('last_burnout_check')
            if not last_check or (datetime.utcnow() - last_check).days >= 1:
                from ai_services.wellness_recommender import WellnessRecommender
                
                # Get user's recent activity for burnout analysis
                recent_commits = user.repositories.with_entities(
                    func.count('*').label('commit_count'),
                    func.sum(Repository.lines_added + Repository.lines_removed).label('total_changes')
                ).filter(
                    Repository.last_commit_date >= datetime.utcnow() - timedelta(days=7)
                ).first()
                
                # Get recent journal sentiment
                recent_entries = user.journal_entries.with_entities(
                    func.avg(JournalEntry.sentiment).label('avg_sentiment'),
                    func.count('*').label('entry_count')
                ).filter(
                    JournalEntry.created_at >= datetime.utcnow() - timedelta(days=7)
                ).first()
                
                # Analyze burnout risk
                recommender = WellnessRecommender()
                risk_result = recommender.analyze_burnout_risk(
                    git_data={
                        'commit_count': recent_commits[0] or 0,
                        'total_changes': recent_commits[1] or 0,
                        'user_id': user.id
                    },
                    journal_data={
                        'avg_sentiment': float(recent_entries[0] or 0),
                        'entry_count': recent_entries[1] or 0
                    }
                )
                
                # Update last check time regardless of result
                user.set_setting('last_burnout_check', datetime.utcnow())
                
                # Only send alert for moderate or high risk
                if risk_result['risk_level'] in ['moderate', 'high']:
                    NotificationManager.send_burnout_alert(
                        user=user,
                        risk_level=risk_result['risk_level'],
                        suggestions=risk_result['suggested_interventions']
                    )
        
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error scheduling wellness notifications: {str(e)}", exc_info=True)
        db.session.rollback()

import random
from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

class WellnessRecommender:
    """
    Provides wellness recommendations based on developer activity and journal entries.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize the WellnessRecommender with optional ML model path.
        
        Args:
            model_path: Path to load a pre-trained ML model (optional)
        """
        self.model = self._load_model(model_path) if model_path else None
        self.scaler = StandardScaler()
        self.user_preferences = {}
        self.last_recommendations = {}
        
        # Initialize recommendation templates with evidence-based practices
        self.recommendation_templates = {
            'break_reminders': [
                ("Consider a 5-minute break after 50 minutes of focused work. "
                 "Research shows this improves focus and reduces eye strain.", 0.8),
                ("Time for a microbreak! Look away from your screen for 20 seconds "
                 "to reduce digital eye strain.", 0.7),
                ("You've been working for a while. Try the 20-20-20 rule: every 20 minutes, "
                 "look at something 20 feet away for 20 seconds.", 0.9)
            ],
            'journaling_prompts': [
                ("Reflect on your current emotional state. What's contributing to it?", 0.7),
                ("Write about a challenge you're facing and possible solutions.", 0.6),
                ("List three things that went well today and why.", 0.8)
            ],
            'work_schedule': [
                ("Consider adjusting your work hours to match your natural energy levels. "
                 "Your most productive hours seem to be in the morning.", 0.7),
                ("Try time-blocking your schedule to align with your energy levels "
                 "throughout the day.", 0.8)
            ],
            'mental_health': [
                ("Practice the 4-7-8 breathing technique: inhale for 4s, hold for 7s, "
                 "exhale for 8s. Repeat 4 times.", 0.9),
                ("Consider a short mindfulness meditation to reduce stress and "
                 "improve focus.", 0.85)
            ],
            'productivity': [
                ("Try the Pomodoro technique: 25 minutes of focused work followed by "
                 "a 5-minute break.", 0.85),
                ("Prioritize your tasks using the Eisenhower Matrix to focus on what's "
                 "important and urgent.", 0.8)
            ]
        }
        
        # Burnout risk factors and their weights
        self.burnout_factors = {
            'long_hours': 0.25,
            'high_commit_frequency': 0.2,
            'irregular_schedule': 0.15,
            'negative_sentiment': 0.3,
            'low_social_interaction': 0.1
        }
    
    def _load_model(self, model_path: str):
        """Load a pre-trained ML model if available."""
        if model_path and os.path.exists(model_path):
            return joblib.load(model_path)
        return None
    
    def _save_model(self, model_path: str):
        """Save the trained model and related data to disk."""
        if self.model:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'user_preferences': self.user_preferences,
                'feature_importance': getattr(self, 'feature_importance', {})
            }, model_path)
    
    def record_feedback(self, category: str, feedback: Dict):
        """Record user feedback on recommendations for ML training.
        
        Args:
            category: The recommendation category
            feedback: Dict containing 'accepted' (bool) and optionally 'engagement' (0-1)
        """
        if category not in self.last_recommendations:
            return
            
        # Store feedback with context
        feedback_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'category': category,
            'recommendation': self.last_recommendations[category],
            'feedback': feedback
        }
        
        if not hasattr(self, 'user_feedback'):
            self.user_feedback = []
        self.user_feedback.append(feedback_entry)
        
        # Update user preferences based on feedback
        if feedback.get('accepted', False):
            if category not in self.user_preferences:
                self.user_preferences[category] = {'engagement': 0.5}
            
            # Increase engagement score for accepted recommendations (capped at 1.0)
            engagement = feedback.get('engagement', 0.7)
            current = self.user_preferences[category].get('engagement', 0.5)
            self.user_preferences[category]['engagement'] = min(1.0, current + 0.1 * engagement)
    
    def train_model(self, training_data=None):
        """Train or update the recommendation model based on collected feedback."""
        feedback_data = training_data or getattr(self, 'user_feedback', [])
        if not feedback_data:
            return  # No data to train on
            
        # Initialize model if needed
        if self.model is None:
            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42
            )
        
        # Convert feedback to training examples
        X = []
        y = []
        
        for entry in feedback_data:
            if 'context' not in entry.get('recommendation', {}):
                continue
                
            # Extract features from context
            context = entry['recommendation']['context']
            features = [
                context.get('time_of_day', 0) / 24.0,
                context.get('day_of_week', 0) / 7.0,
                context.get('sentiment', 0.0) * 0.5 + 0.5,  # Scale -1..1 to 0..1
                self.user_preferences.get(entry['category'], {}).get('engagement', 0.5)
            ]
            
            # Label is 1 for accepted recommendations, 0 for rejected
            label = 1 if entry.get('feedback', {}).get('accepted', False) else 0
            
            X.append(features)
            y.append(label)
        
        if not X:
            return  # No valid training examples
            
        # Train the model
        self.model.fit(X, y)
    
    def _calculate_burnout_risk_score(self, git_data: Dict, journal_data: Dict) -> float:
        """Calculate a burnout risk score based on git and journal data."""
        risk_score = 0.0
        
        # Calculate risk based on working hours
        if git_data.get('weekly_hours', 0) > 50:  # More than 50 hours/week
            risk_score += self.burnout_factors['long_hours'] * 1.0
        elif git_data.get('weekly_hours', 0) > 40:
            risk_score += self.burnout_factors['long_hours'] * 0.7
            
        # Check for high commit frequency (potential overwork)
        if git_data.get('avg_daily_commits', 0) > 10:
            risk_score += self.burnout_factors['high_commit_frequency'] * 0.8
            
        # Check for irregular work schedule
        if git_data.get('schedule_regularity', 0) < 0.5:  # 0-1 scale, lower is more irregular
            risk_score += self.burnout_factors['irregular_schedule'] * 0.6
            
        # Check for negative sentiment in journal entries
        if journal_data.get('avg_sentiment', 0) < -0.3:
            risk_score += self.burnout_factors['negative_sentiment'] * 0.9
            
        # Check for low social interaction (fewer commits with multiple authors)
        if git_data.get('collaboration_score', 0) < 0.3:
            risk_score += self.burnout_factors['low_social_interaction'] * 0.5
            
        return min(1.0, max(0.0, risk_score))  # Ensure score is between 0 and 1
    
    def _get_personalized_recommendation(self, category: str, user_context: Dict) -> Tuple[str, float]:
        """Get a personalized recommendation from a specific category.
        
        Args:
            category: The recommendation category (e.g., 'break_reminders', 'journaling_prompts')
            user_context: Dictionary containing user context like 'avg_sentiment', 'recent_activity', etc.
            
        Returns:
            Tuple of (recommendation_text, confidence_score)
        """
        if category not in self.recommendation_templates:
            return "", 0.0
            
        # Get current time features
        now = datetime.now()
        current_hour = now.hour
        day_of_week = now.weekday()  # 0 = Monday, 6 = Sunday
        
        # Get user preferences for this category
        user_pref = self.user_preferences.get(category, {})
        
        # Calculate time-based weights
        time_weights = {
            'morning': 1.0 + (0.3 if 5 <= current_hour < 10 else 0),
            'afternoon': 1.0 + (0.3 if 12 <= current_hour < 17 else 0),
            'evening': 1.0 + (0.3 if 17 <= current_hour < 22 else 0),
            'weekend': 1.2 if day_of_week >= 5 else 1.0
        }
        
        # Calculate recommendation scores with personalization
        valid_recs = []
        for rec_text, base_score in self.recommendation_templates[category]:
            score = base_score
            
            # Time-based personalization
            rec_time = 'any'
            if any(time_word in rec_text.lower() for time_word in ['morning', 'breakfast', 'start your day']):
                rec_time = 'morning'
            elif any(time_word in rec_text.lower() for time_word in ['afternoon', 'lunch']):
                rec_time = 'afternoon'
            elif any(time_word in rec_text.lower() for time_word in ['evening', 'night', 'dinner']):
                rec_time = 'evening'
                
            # Apply time-based weight
            score *= time_weights.get(rec_time, 1.0)
            
            # Apply weekend boost for certain activities
            if 'weekend' in rec_text.lower() and day_of_week >= 5:
                score *= time_weights['weekend']
                
            # Apply ML-based personalization if model is available
            if hasattr(self, 'model') and self.model is not None:
                try:
                    # Prepare features for ML model
                    features = [
                        current_hour / 24.0,  # Time of day (0-1)
                        day_of_week / 7.0,    # Day of week (0-1)
                        user_context.get('avg_sentiment', 0.0) * 0.5 + 0.5,  # Scale -1..1 to 0..1
                        user_context.get('recent_activity', 0.5),  # 0-1 scale
                        user_pref.get('engagement', 0.5)  # User's historical engagement
                    ]
                    
                    # Get prediction from model (probability of positive engagement)
                    prediction = self.model.predict_proba([features])[0][1]
                    
                    # Scale prediction to 0.5-1.5 range to adjust score
                    ml_weight = 0.5 + prediction  # 0.5-1.5 range
                    score *= ml_weight
                    
                except Exception as e:
                    # Fallback to base score if model prediction fails
                    pass
            
            # Store recommendation with metadata
            valid_recs.append({
                'text': rec_text,
                'score': score,
                'category': category,
                'features': {
                    'time_of_day': current_hour,
                    'day_of_week': day_of_week,
                    'sentiment': user_context.get('avg_sentiment', 0.0),
                    'recent_activity': user_context.get('recent_activity', 0.5)
                }
            })
        
        if not valid_recs:
            return "", 0.0
            
        # Sort by score and select top recommendation
        valid_recs.sort(key=lambda x: x['score'], reverse=True)
        top_rec = valid_recs[0]
        
        # Store for feedback collection
        self.last_recommendations[category] = {
            'timestamp': now.isoformat(),
            'recommendation': top_rec['text'],
            'score': top_rec['score'],
            'context': top_rec['features']
        }
        
        return top_rec['text'], top_rec['score']
    
    def generate_daily_tips(self, user_data: Dict) -> List[Dict]:
        """Generate personalized daily wellness tips based on user data."""
        tips = []
        
        # Add time-based tip
        current_hour = datetime.now().hour
        if 5 <= current_hour < 10:
            tips.append({
                'text': "Start your day with a short planning session",
                'category': 'productivity',
                'priority': 'high'
            })
        
        # Add activity-based tips
        if user_data.get('hours_since_last_break', 0) > 1:
            tip, score = self._get_personalized_recommendation('break_reminders', user_data)
            if tip:
                tips.append({
                    'text': tip,
                    'category': 'break_reminders',
                    'priority': 'high' if score > 0.7 else 'medium'
                })
        
        # Add journaling prompt if it's been a while since last entry
        if user_data.get('days_since_last_journal', 0) > 2:
            tip, score = self._get_personalized_recommendation('journaling_prompts', user_data)
            if tip:
                tips.append({
                    'text': f"Journal Prompt: {tip}",
                    'category': 'journaling',
                    'priority': 'medium'
                })
        
        # Add work-life balance tip
        if user_data.get('work_life_balance_score', 0) < 0.5:
            tip, score = self._get_personalized_recommendation('work_schedule', user_data)
            if tip:
                tips.append({
                    'text': f"Work-Life Tip: {tip}",
                    'category': 'work_life_balance',
                    'priority': 'high' if score > 0.8 else 'medium'
                })
        
        return tips
    
    def analyze_burnout_risk(self, git_data: Dict, journal_data: Dict) -> Dict:
        """Analyze burnout risk based on git activity and journal entries."""
        risk_score = self._calculate_burnout_risk_score(git_data, journal_data)
        
        # Determine risk level
        if risk_score > 0.7:
            risk_level = 'high'
        elif risk_score > 0.4:
            risk_level = 'moderate'
        else:
            risk_level = 'low'
        
        # Get recommendations based on risk level
        interventions = self.suggest_interventions(risk_level, {})
        
        return {
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'interventions': interventions,
            'factors': {
                'work_hours': git_data.get('weekly_hours', 0),
                'commit_frequency': git_data.get('avg_daily_commits', 0),
                'schedule_regularity': git_data.get('schedule_regularity', 0),
                'sentiment': journal_data.get('avg_sentiment', 0),
                'social_interaction': git_data.get('collaboration_score', 0)
            }
        }
    
    def suggest_interventions(self, risk_level: str, user_preferences: Dict) -> List[Dict]:
        """Suggest interventions based on burnout risk level and user preferences."""
        interventions = []
        
        if risk_level == 'high':
            interventions.extend([
                {
                    'type': 'immediate_break',
                    'title': 'Take an Immediate Break',
                    'description': 'Step away from work for at least 30 minutes. Take a walk outside if possible.',
                    'priority': 'critical'
                },
                {
                    'type': 'schedule_review',
                    'title': 'Schedule Time Off',
                    'description': 'Plan at least 1-2 days off in the next week to recover.',
                    'priority': 'high'
                },
                {
                    'type': 'professional_help',
                    'title': 'Consider Professional Support',
                    'description': 'Speak with a mental health professional about stress management.',
                    'priority': 'high'
                }
            ])
        elif risk_level == 'moderate':
            interventions.extend([
                {
                    'type': 'microbreaks',
                    'title': 'Schedule Regular Microbreaks',
                    'description': 'Take 5-minute breaks every 50 minutes to stretch and rest your eyes.',
                    'priority': 'medium'
                },
                {
                    'type': 'workload_review',
                    'title': 'Review Workload',
                    'description': 'Identify tasks that can be delegated or postponed.',
                    'priority': 'medium'
                },
                {
                    'type': 'mindfulness',
                    'title': 'Practice Mindfulness',
                    'description': 'Try a 5-minute guided meditation to reduce stress.',
                    'priority': 'medium'
                }
            ])
        else:  # low risk
            interventions.extend([
                {
                    'type': 'preventive_breaks',
                    'title': 'Maintain Healthy Habits',
                    'description': 'Continue taking regular breaks and maintaining work-life balance.',
                    'priority': 'low'
                },
                {
                    'type': 'self_reflection',
                    'title': 'Reflect on Well-being',
                    'description': 'Journal about your current work habits and well-being.',
                    'priority': 'low'
                }
            ])
        
        return interventions
    
    def get_work_life_balance_tips(self, commit_patterns: Dict) -> List[Dict]:
        """Generate work-life balance tips based on commit patterns."""
        tips = []
        
        # Check for late-night commits
        if commit_patterns.get('late_night_commits', 0) > 2:  # More than 2 late-night commits
            tips.append({
                'title': 'Late-Night Work Detected',
                'suggestion': 'Consider scheduling work during core hours to maintain a healthy sleep schedule.',
                'priority': 'high'
            })
        
        # Check for weekend work
        if commit_patterns.get('weekend_commit_ratio', 0) > 0.3:  # More than 30% of commits on weekends
            tips.append({
                'title': 'Weekend Work Detected',
                'suggestion': 'Try to keep weekends free for rest and personal time to prevent burnout.',
                'priority': 'medium'
            })
        
        # Check for long stretches without breaks
        if commit_patterns.get('max_commit_streak_hours', 0) > 4:  # More than 4 hours of continuous work
            tips.append({
                'title': 'Long Work Sessions Detected',
                'suggestion': 'Take regular breaks during long work sessions to maintain focus and prevent fatigue.',
                'priority': 'medium'
            })
        
        # Add general work-life balance tips if no specific issues found
        if not tips:
            tips.append({
                'title': 'Maintain Work-Life Balance',
                'suggestion': 'Consider setting clear boundaries between work and personal time to maintain balance.',
                'priority': 'low'
            })
        
        return tips
        
        return random.choice(recommendations)
    
    def get_journal_insights(self, journal_entries):
        """Generate insights from journal entries."""
        if not journal_entries:
            return None
            
        # Simple sentiment analysis (in a real app, you might use the sentiment analyzer)
        positive_entries = [e for e in journal_entries if e.get('sentiment_score', 0) > 0.2]
        negative_entries = [e for e in journal_entries if e.get('sentiment_score', 0) < -0.2]
        
        insights = []
        
        if len(positive_entries) > len(negative_entries) * 2:
            insights.append("Your recent journal entries have been mostly positive. Keep up the good work!")
        elif len(negative_entries) > len(positive_entries):
            insights.append("You've had some challenging days recently. Remember to take care of yourself.")
        
        # Look for patterns in entry times
        entry_times = [e.get('created_at').hour for e in journal_entries if e.get('created_at')]
        if entry_times:
            avg_entry_hour = sum(entry_times) / len(entry_times)
            if avg_entry_hour > 20:
                insights.append("You often journal in the evening. This can be a great way to reflect on your day.")
            elif avg_entry_hour < 10:
                insights.append("You prefer morning journaling. This is a great way to set intentions for the day.")
        
        return insights if insights else None
    
    def get_daily_wellness_plan(self):
        """Generate a daily wellness plan."""
        return {
            'morning': [
                "Start with 5 minutes of stretching or light exercise",
                "Set 3 main goals for the day",
                "Eat a healthy breakfast"
            ],
            'work_session': [
                "Use the Pomodoro technique (25 min work, 5 min break)",
                "Take a short walk after completing each major task",
                "Stay hydrated and take regular screen breaks"
            ],
            'evening': [
                "Reflect on 3 things that went well today",
                "Disconnect from screens 30 minutes before bed",
                "Prepare for tomorrow by reviewing your schedule"
            ]
        }

import random
from datetime import datetime, time

class WellnessRecommender:
    """
    Provides wellness recommendations based on developer activity and journal entries.
    """
    
    def __init__(self):
        # Define recommendation categories
        self.categories = {
            'physical': [
                "Take a 5-minute stretch break",
                "Try the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds",
                "Do some quick desk exercises or take a short walk",
                "Check your posture and adjust your chair/desk setup",
                "Hydrate! Have a glass of water"
            ],
            'mental': [
                "Practice deep breathing for 1 minute",
                "Try a quick meditation or mindfulness exercise",
                "Take a short break to clear your mind",
                "Write down three things you're grateful for",
                "Listen to calming music for a few minutes"
            ],
            'productivity': [
                "Prioritize your tasks for the next hour",
                "Try the Pomodoro technique: 25 minutes work, 5 minutes break",
                "Review and organize your to-do list",
                "Eliminate distractions for focused work",
                "Break down a large task into smaller, manageable chunks"
            ],
            'social': [
                "Reach out to a colleague for a quick chat",
                "Schedule a virtual coffee break with a teammate",
                "Share something you learned with your team",
                "Give someone a compliment",
                "Ask for help or input on a challenge you're facing"
            ]
        }
    
    def get_time_based_recommendation(self):
        """Get a recommendation based on the time of day."""
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 10:
            # Morning recommendations
            return random.choice([
                "Start your day with a short planning session",
                "Begin with your most important task of the day",
                "Set your top 3 priorities for the day"
            ])
        elif 10 <= current_hour < 12:
            # Late morning
            return random.choice([
                "Take a short break and stretch",
                "Review your morning progress",
                "Have a healthy snack to keep your energy up"
            ])
        elif 12 <= current_hour < 14:
            # Lunch time
            return random.choice([
                "Step away from your desk for lunch",
                "Take a short walk after eating",
                "Use this time to disconnect and recharge"
            ])
        elif 14 <= current_hour < 16:
            # Afternoon slump
            return random.choice([
                "Try a quick energy-boosting activity",
                "Work on a different task to stay engaged",
                "Take a short break and get some fresh air"
            ])
        else:
            # Evening
            return random.choice([
                "Review your accomplishments for the day",
                "Plan for tomorrow",
                "Start winding down your work"
            ])
    
    def get_activity_based_recommendation(self, activity_data):
        """Get a recommendation based on recent activity data."""
        recommendations = []
        
        # Check for long coding sessions without breaks
        if activity_data.get('hours_since_last_break', 0) > 1:
            recommendations.append("You've been working for a while. Consider taking a short break to recharge.")
        
        # Check for high stress indicators
        if activity_data.get('recent_sentiment', {}).get('score', 0) < -0.5:
            recommendations.append("You seem to be having a tough time. Try a quick mindfulness exercise or take a short walk to clear your mind.")
        
        # Check for low activity
        if activity_data.get('recent_commit_count', 0) == 0 and activity_data.get('active_hours', 0) > 2:
            recommendations.append("You've been at your desk for a while without much activity. Try a quick stretch or change of scenery.")
        
        # Default to time-based if no specific recommendations
        if not recommendations:
            return self.get_time_based_recommendation()
        
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

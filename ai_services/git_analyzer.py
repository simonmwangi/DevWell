import os
import git
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
import git
import os
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from textblob import TextBlob
import numpy as np

@dataclass
class CommitAnalysis:
    hash: str
    timestamp: datetime
    author: str
    message: str
    sentiment: float
    is_late_night: bool
    is_weekend: bool
    files_changed: int
    insertions: int
    deletions: int

class GitAnalyzer:
    def __init__(self):
        self.repo: Optional[git.Repo] = None
        self.commits_analysis: List[CommitAnalysis] = []
    
    def _get_commit_sentiment(self, message: str) -> float:
        """Analyze sentiment of a commit message."""
        analysis = TextBlob(message)
        return analysis.sentiment.polarity  # Range from -1 to 1
    
    def _is_late_night_commit(self, commit_time: datetime) -> bool:
        """Check if commit was made late at night (10 PM to 4 AM)."""
        return commit_time.hour >= 22 or commit_time.hour < 4
    
    def _is_weekend_commit(self, commit_time: datetime) -> bool:
        """Check if commit was made on a weekend."""
        return commit_time.weekday() >= 5  # 5=Saturday, 6=Sunday
    
    def analyze_repository(self, repo_path: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a git repository.
        
        Args:
            repo_path: Path to the git repository
            days_back: Number of days to analyze (default: 30)
            
        Returns:
            Dict containing analysis results
        """
        try:
            self.repo = git.Repo(repo_path)
            since_date = datetime.now() - timedelta(days=days_back)
            
            # Reset analysis data
            self.commits_analysis = []
            
            # Get all commits within the specified time range
            commits = list(self.repo.iter_commits(since=since_date))
            
            # Initialize metrics
            metrics = {
                'commit_patterns': self.get_commit_patterns(repo_path, commits),
                'sentiment_analysis': self.analyze_commit_sentiment(commits),
                'burnout_indicators': self.detect_burnout_indicators(commits),
                'productivity_metrics': self.get_productivity_metrics(commits),
                'file_analysis': self.analyze_file_changes(commits),
                'time_analysis': self.analyze_commit_timing(commits),
            }
            
            return metrics
            
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Invalid git repository: {repo_path}")
        except Exception as e:
            raise Exception(f"Error analyzing repository: {str(e)}")
    
    def get_commit_patterns(self, repo_path: str, commits: Optional[List[git.Commit]] = None) -> Dict[str, Any]:
        """Analyze commit timing and frequency patterns."""
        if commits is None:
            commits = list(self.repo.iter_commits())
        
        if not commits:
            return {}
            
        # Analyze commit times
        commit_times = [commit.committed_datetime for commit in commits]
        commit_hours = [dt.hour for dt in commit_times]
        commit_days = [dt.weekday() for dt in commit_times]  # 0=Monday, 6=Sunday
        
        return {
            'total_commits': len(commits),
            'commit_frequency': len(commits) / 30,  # per day average
            'commit_hour_distribution': dict(Counter(commit_hours)),
            'commit_day_distribution': dict(Counter(commit_days)),
            'avg_commits_per_day': len(commits) / len(set(dt.date() for dt in commit_times)) if commits else 0,
        }
    
    def analyze_commit_sentiment(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze sentiment trends in commit messages."""
        if not commits:
            return {}
            
        sentiments = []
        for commit in commits:
            sentiment = self._get_commit_sentiment(commit.message)
            sentiments.append(sentiment)
            
        return {
            'avg_sentiment': np.mean(sentiments) if sentiments else 0,
            'sentiment_trend': list(sentiments[-30:]),  # Last 30 commits
            'positive_commits_ratio': sum(1 for s in sentiments if s > 0.1) / len(sentiments) if sentiments else 0,
            'negative_commits_ratio': sum(1 for s in sentiments if s < -0.1) / len(sentiments) if sentiments else 0,
        }
    
    def _make_tz_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
        
    def detect_burnout_indicators(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Detect potential burnout indicators from commit history."""
        if not commits:
            return {}
            
        # Analyze recent commits (last 14 days)
        recent_cutoff = self._make_tz_aware(datetime.utcnow() - timedelta(days=14))
        recent_commits = [c for c in commits if self._make_tz_aware(c.committed_datetime) >= recent_cutoff]
        
        # Count late night and weekend commits
        late_night = sum(1 for c in commits if self._is_late_night_commit(self._make_tz_aware(c.committed_datetime)))
        weekend = sum(1 for c in commits if self._is_weekend_commit(self._make_tz_aware(c.committed_datetime).replace(tzinfo=None)))
        
        # Calculate message quality (simple heuristic based on message length)
        message_quality = np.mean([min(len(c.message.strip()), 50) / 50 for c in commits]) if commits else 0
        
        return {
            'late_night_commits': late_night,
            'weekend_commits': weekend,
            'message_quality_score': message_quality,
            'recent_commit_frequency': len(recent_commits) / 14,  # per day
            'burnout_risk': self._calculate_burnout_risk(commits),
        }
    
    def get_productivity_metrics(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Calculate various productivity metrics."""
        if not commits:
            return {}
            
        # Group commits by day
        commits_by_day = defaultdict(list)
        for commit in commits:
            day = commit.committed_datetime.date()
            commits_by_day[day].append(commit)
            
        # Calculate daily metrics
        daily_metrics = []
        for day, day_commits in commits_by_day.items():
            daily_metrics.append({
                'date': day.isoformat(),
                'commit_count': len(day_commits),
                'is_weekend': day.weekday() >= 5,
            })
            
        return {
            'daily_metrics': sorted(daily_metrics, key=lambda x: x['date']),
            'avg_commits_per_day': len(commits) / len(commits_by_day) if commits_by_day else 0,
            'busiest_day': max(commits_by_day.items(), key=lambda x: len(x[1]))[0].isoformat() if commits_by_day else None,
        }
    
    def analyze_file_changes(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze file change patterns."""
        if not commits:
            return {}
            
        file_changes = defaultdict(lambda: {'insertions': 0, 'deletions': 0, 'commits': 0})
        
        for commit in commits:
            try:
                for file in commit.stats.files.values():
                    file_changes[file['filename']]['insertions'] += file['insertions']
                    file_changes[file['filename']]['deletions'] += file['deletions']
                    file_changes[file['filename']]['commits'] += 1
            except (AttributeError, KeyError):
                continue
                
        # Get top changed files
        top_changed = sorted(
            [{'file': k, **v} for k, v in file_changes.items()],
            key=lambda x: x['commits'],
            reverse=True
        )[:10]
        
        return {
            'top_changed_files': top_changed,
            'total_files_changed': len(file_changes),
            'total_insertions': sum(f['insertions'] for f in file_changes.values()),
            'total_deletions': sum(f['deletions'] for f in file_changes.values()),
        }
    
    def analyze_commit_timing(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze commit timing patterns."""
        if not commits:
            return {}
            
        # Group commits by hour and day
        hourly = defaultdict(int)
        daily = defaultdict(int)
        
        for commit in commits:
            dt = commit.committed_datetime
            hourly[dt.hour] += 1
            daily[dt.weekday()] += 1
            
        return {
            'hourly_commits': dict(sorted(hourly.items())),
            'daily_commits': dict(sorted(daily.items())),
            'late_night_ratio': sum(1 for c in commits if self._is_late_night_commit(c.committed_datetime)) / len(commits),
            'weekend_ratio': sum(1 for c in commits if self._is_weekend_commit(c.committed_datetime)) / len(commits),
        }
    
    def _calculate_burnout_risk(self, commits: List[git.Commit]) -> float:
        """Calculate a burnout risk score (0-1)."""
        if not commits:
            return 0.0
            
        risk_factors = []
        
        # 1. Late night commits
        late_night = sum(1 for c in commits if self._is_late_night_commit(c.committed_datetime))
        risk_factors.append(min(late_night / len(commits) * 2, 1.0))  # Up to 50% weight
        
        # 2. Weekend work
        weekend = sum(1 for c in commits if self._is_weekend_commit(c.committed_datetime))
        risk_factors.append(min(weekend / len(commits) * 2, 1.0))  # Up to 50% weight
        
        # 3. Negative sentiment trend (last 10% of commits)
        if len(commits) > 10:
            recent = commits[:len(commits)//10]
            sentiments = [self._get_commit_sentiment(c.message) for c in recent]
            if len(sentiments) > 1:
                trend = (sentiments[-1] - np.mean(sentiments[:-1])) / (1 if np.mean(sentiments[:-1]) == 0 else abs(np.mean(sentiments[:-1])))
                risk_factors.append(max(0, min(-trend, 1.0)))  # Negative trend increases risk
        
        # 4. Erratic commit patterns (variance in daily commits)
        if len(commits) > 7:
            daily_counts = defaultdict(int)
            for c in commits:
                daily_counts[c.committed_datetime.date()] += 1
            if len(daily_counts) > 1:
                variance = np.var(list(daily_counts.values()))
                risk_factors.append(min(variance / 10, 1.0))  # High variance increases risk
        
        return min(sum(risk_factors) / len(risk_factors), 1.0) if risk_factors else 0.0

def analyze_commit_patterns(repo_path):
    """
    Analyze commit patterns in a git repository.
    
    Args:
        repo_path (str): Path to the git repository
        
    Returns:
        dict: Dictionary containing various commit statistics and patterns
    """
    try:
        repo = git.Repo(repo_path)
        
        # Initialize data structures
        commits = list(repo.iter_commits())
        authors = defaultdict(int)
        files_changed = defaultdict(int)
        hourly_commits = defaultdict(int)
        daily_commits = defaultdict(int)
        
        # Process commits
        for commit in commits:
            # Count commits by author
            authors[commit.author.name] += 1
            
            # Count file changes
            for file in commit.stats.files.keys():
                files_changed[file] += 1
            
            # Track commit times
            commit_time = commit.committed_datetime
            hour = commit_time.hour
            day = commit_time.strftime('%A')
            
            hourly_commits[hour] += 1
            daily_commits[day] += 1
        
        # Calculate productivity metrics
        first_commit = commits[-1].committed_datetime if commits else None
        last_commit = commits[0].committed_datetime if commits else None
        
        total_days = (last_commit - first_commit).days if first_commit and last_commit else 1
        commits_per_day = len(commits) / total_days if total_days > 0 else 0
        
        # Get most active hour and day
        most_active_hour = max(hourly_commits.items(), key=lambda x: x[1]) if hourly_commits else (None, 0)
        most_active_day = max(daily_commits.items(), key=lambda x: x[1]) if daily_commits else (None, 0)
        
        # Get most active files
        most_active_files = sorted(files_changed.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_commits': len(commits),
            'total_authors': len(authors),
            'first_commit': first_commit.isoformat() if first_commit else None,
            'last_commit': last_commit.isoformat() if last_commit else None,
            'commits_per_day': round(commits_per_day, 2),
            'most_active_author': max(authors.items(), key=lambda x: x[1]) if authors else (None, 0),
            'most_active_hour': {
                'hour': most_active_hour[0],
                'commits': most_active_hour[1]
            },
            'most_active_day': {
                'day': most_active_day[0],
                'commits': most_active_day[1]
            },
            'top_files': [{'file': f[0], 'changes': f[1]} for f in most_active_files],
            'hourly_pattern': [{'hour': h, 'commits': c} for h, c in sorted(hourly_commits.items())],
            'daily_pattern': [{'day': d, 'commits': c} for d, c in sorted(daily_commits.items())]
        }
        
    except Exception as e:
        print(f"Error analyzing git repository: {str(e)}")
        return {
            'error': str(e),
            'total_commits': 0,
            'total_authors': 0,
            'commits_per_day': 0,
            'top_files': [],
            'hourly_pattern': [],
            'daily_pattern': []
        }

def get_code_churn(repo_path, days=30):
    """
    Calculate code churn (lines added/removed) over time.
    
    Args:
        repo_path (str): Path to the git repository
        days (int): Number of days to look back
        
    Returns:
        list: List of daily code churn statistics
    """
    try:
        repo = git.Repo(repo_path)
        
        # Get commits from the last N days
        since_date = datetime.now() - timedelta(days=days)
        commits = list(repo.iter_commits(since=since_date))
        
        # Group commits by day
        daily_changes = defaultdict(lambda: {'additions': 0, 'deletions': 0, 'commits': 0})
        
        for commit in commits:
            date = commit.committed_datetime.date()
            stats = commit.stats.total
            
            daily_changes[date]['additions'] += stats.get('insertions', 0)
            daily_changes[date]['deletions'] += stats.get('deletions', 0)
            daily_changes[date]['commits'] += 1
        
        # Convert to list of dicts sorted by date
        result = [
            {
                'date': date.isoformat(),
                'additions': data['additions'],
                'deletions': data['deletions'],
                'commits': data['commits'],
                'net_change': data['additions'] - data['deletions']
            }
            for date, data in sorted(daily_changes.items())
        ]
        
        return result
        
    except Exception as e:
        print(f"Error calculating code churn: {str(e)}")
        return []

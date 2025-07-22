import os
import git
from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd

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

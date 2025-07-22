# Import all models to ensure they are registered with SQLAlchemy
from .user import User
from .journal import JournalEntry
from .repository import Repository, Commit

# Make models available at package level
__all__ = ['User', 'JournalEntry', 'Repository', 'Commit']

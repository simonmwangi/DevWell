from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.journal import JournalEntry
from app import db
from ai_services.sentiment_analyzer import analyze_sentiment
from forms import JournalEntryForm
from datetime import datetime

# Create blueprint
journal_bp = Blueprint('journal', __name__)

@journal_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    sentiment_filter = request.args.get('sentiment', type=str)
    
    # Base query
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply sentiment filter if provided
    if sentiment_filter in ['positive', 'neutral', 'negative']:
        query = query.filter_by(sentiment_label=sentiment_filter)
    
    # Get paginated journal entries
    entries = query.order_by(JournalEntry.created_at.desc())\
                 .paginate(page=page, per_page=per_page, error_out=False)
    
    # Get sentiment counts for all entries (not filtered)
    sentiment_counts = db.session.query(
        JournalEntry.sentiment_label,
        db.func.count(JournalEntry.id)
    ).filter_by(user_id=current_user.id)\
     .group_by(JournalEntry.sentiment_label)\
     .all()
    
    # Convert to dictionary for easier access in template
    sentiment_dict = {label: count for label, count in sentiment_counts}

    # --- New aggregated stats for wellness recommendations ---
    sentiment_stats = db.session.query(
        db.func.avg(JournalEntry.sentiment_score).label('avg_sentiment'),
        db.func.avg(db.func.length(JournalEntry.content)).label('avg_length')
    ).filter_by(user_id=current_user.id).first()

    last_entry = JournalEntry.query.filter_by(user_id=current_user.id)\
        .order_by(JournalEntry.created_at.desc()).first()
    last_entry_days_ago = (
        (datetime.utcnow() - last_entry.created_at).days if last_entry else None
    )

    avg_entry_length = (
        float(sentiment_stats.avg_length) if sentiment_stats and sentiment_stats.avg_length else 0
    )
    
    return render_template(
        'journal.html',
        entries=entries,
        sentiment_counts={
            'positive': sentiment_dict.get('positive', 0),
            'neutral': sentiment_dict.get('neutral', 0),
            'negative': sentiment_dict.get('negative', 0)
        },
        current_sentiment=sentiment_filter,
        sentiment_stats=sentiment_stats,
        avg_entry_length=avg_entry_length,
        last_entry_days_ago=last_entry_days_ago
    )

@journal_bp.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    # Ensure the user owns this entry
    if entry.user_id != current_user.id:
        flash('You do not have permission to view this entry', 'danger')
        return redirect(url_for('journal.index'))
    return render_template('journal_entry.html', entry=entry)

@journal_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    form = JournalEntryForm()
    
    if form.validate_on_submit():
        # Analyze sentiment
        sentiment = analyze_sentiment(form.content.data)
        
        entry = JournalEntry(
            title=form.title.data,
            content=form.content.data,
            user_id=current_user.id,
            sentiment_score=sentiment['score'],
            sentiment_label=sentiment['label']
        )
        
        db.session.add(entry)
        db.session.commit()
        
        flash('Journal entry created successfully!', 'success')
        return redirect(url_for('journal.view_entry', entry_id=entry.id))
    
    return render_template('journal_form.html', form=form, title='New Journal Entry')

@journal_bp.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    
    # Ensure the user owns this entry
    if entry.user_id != current_user.id:
        flash('You do not have permission to edit this entry', 'danger')
        return redirect(url_for('journal.index'))
    
    if request.method == 'POST':
        entry.title = request.form.get('title', entry.title)
        entry.content = request.form.get('content', entry.content)
        
        # Re-analyze sentiment if content changed
        if entry.content != request.form.get('content'):
            sentiment = analyze_sentiment(entry.content)
            entry.sentiment_score = sentiment['score']
            entry.sentiment_label = sentiment['label']
        
        db.session.commit()
        flash('Entry updated successfully!', 'success')
        return redirect(url_for('journal.view_entry', entry_id=entry.id))
    
    return render_template('journal_form.html', entry=entry)

@journal_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    
    # Ensure the user owns this entry
    if entry.user_id != current_user.id:
        flash('You do not have permission to delete this entry', 'danger')
        return redirect(url_for('journal.index'))
    
    db.session.delete(entry)
    db.session.commit()
    
    flash('Entry deleted successfully!', 'success')
    return redirect(url_for('journal.index'))

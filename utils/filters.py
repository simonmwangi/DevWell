import markdown2
from markupsafe import Markup

def register_filters(app):
    """Register custom template filters."""
    
    @app.template_filter('markdown')
    def markdown_to_html(text):
        """Convert markdown text to HTML."""
        if not text:
            return ''
        # Convert markdown to HTML and mark it as safe
        html = markdown2.markdown(text)
        return Markup(html)
    
    return app

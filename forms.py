from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    HiddenField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    EqualTo,
    ValidationError,
    Optional,
    URL,
)
from models.user import User
from models.repository import Repository
from models.journal import JournalEntry


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=4, max=20)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    terms = BooleanField(
        "I accept the terms and conditions", validators=[DataRequired()]
    )
    submit = SubmitField("Sign Up")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(
                "That username is already taken. Please choose a different one."
            )

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(
                "That email is already registered. Please use a different one."
            )


class RepositoryForm(FlaskForm):
    """Form for adding or editing a repository."""

    repo_id = HiddenField("Repository ID")
    name = StringField(
        "Repository Name", validators=[DataRequired(), Length(min=2, max=100)]
    )
    repo_url = StringField(
        "Repository URL",
        validators=[DataRequired(), URL(message="Please enter a valid URL")],
    )
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save Repository")

    def __init__(self, current_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

    def validate_name(self, name):
        # Skip validation for existing repository being edited
        if (
            self.repo_id.data
            and str(Repository.query.get(self.repo_id.data).id) == self.repo_id.data
        ):
            return

        repo = Repository.query.filter_by(
            name=name.data, user_id=self.current_user.id
        ).first()

        if repo:
            raise ValidationError(
                "You already have a repository with this name. Please choose a different name."
            )

    def validate_repo_url(self, repo_url):
        # Skip validation for existing repository being edited
        if (
            self.repo_id.data
            and str(Repository.query.get(self.repo_id.data).id) == self.repo_id.data
        ):
            return

        repo = Repository.query.filter_by(
            repo_url=repo_url.data, user_id=self.current_user.id
        ).first()

        if repo:
            raise ValidationError(
                "A repository with this URL already exists in your account."
            )


class JournalEntryForm(FlaskForm):
    """Form for creating or editing a journal entry."""

    id = HiddenField("Entry ID")
    title = StringField(
        "Title",
        validators=[
            DataRequired(),
            Length(
                min=2,
                max=200,
                message="Title must be between 2 and 200 characters long",
            ),
        ],
    )
    content = TextAreaField(
        "Content",
        validators=[
            DataRequired(message="Please enter some content for your journal entry"),
            Length(
                min=10,
                message="Your journal entry should be at least 10 characters long",
            ),
        ],
    )
    submit = SubmitField("Save Entry")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_content(self, content):
        # Add any custom validation for journal content if needed
        if len(content.data.strip()) < 10:
            raise ValidationError(
                "Your journal entry seems too short. Please provide more details."
            )

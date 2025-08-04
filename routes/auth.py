from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
)
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from extensions import db
from forms import LoginForm, RegistrationForm
from utils.email import send_email
from utils.token import generate_confirmation_token, confirm_token
from datetime import datetime

# Create blueprint
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def home():
    return render_template("landing.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.verify_password(form.password.data):
            if not user.confirmed:
                flash("Please confirm your email first.", "warning")
                return redirect(url_for("auth.login"))

            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        flash("Invalid username or password", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Create new user - the form validation already checks for existing username/email
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
            )

            db.session.add(new_user)
            db.session.commit()

            token = generate_confirmation_token(new_user.email)
            confirm_url = url_for("auth.confirm_email", token=token, _external=True)
            print("Confirm url", confirm_url)
            html = render_template("emails/confirm.html", confirm_url=confirm_url)
            send_email(new_user.email, "Confirm Your Email Address", html)

            # flash("Registration successful! Please log in.", "success")
            flash("A confirmation email has been sent.", "info")
            return redirect(url_for("auth.login"))

        except Exception as e:
            db.session.rollback()
            print("Exception ", e)
            flash("An error occurred during registration. Please try again.", "danger")

    return render_template("register.html", form=form)


@auth_bp.route("/confirm/<token>")
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash("Confirmation link is invalid or expired.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash("Account already confirmed. Please log in.", "success")
    else:
        user.confirmed = True
        user.confirmed_on = datetime.utcnow()
        db.session.commit()
        flash("Account confirmed. You can now log in.", "success")

    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

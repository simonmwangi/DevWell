from flask_mail import Message
from extensions import mail


def send_email(to, subject, html):
    msg = Message(subject, recipients=[to], html=html)
    mail.send(msg)

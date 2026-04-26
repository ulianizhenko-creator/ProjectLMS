from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    register_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_games = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    best_score = db.Column(db.Integer, default=0)

    def get_average_score(self):
        """Расчет среднего балла"""
        if self.total_games > 0:
            return round(self.total_score / self.total_games, 2)
        return 0


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    date_played = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('results', lazy=True))
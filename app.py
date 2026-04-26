from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import requests
import json
import os
from models import db, User, QuizResult, Question
from utils import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-for-travel-quiz-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel_quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Глобальные вопросы
QUESTIONS = load_questions_from_csv('quiz_data.csv')
QUESTIONS_PER_GAME = 25  # Все вопросы из викторины


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_fun_fact():
    """Получение интересного факта о путешествиях (API)"""
    try:
        # Используем REST API с фактами
        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en", timeout=5)
        if response.status_code == 200:
            fact = response.json().get('text', '')
            return f"✈️ Интересный факт: {fact[:150]}"
    except:
        pass
    return "🌍 Путешествия расширяют кругозор и делают нас счастливее!"


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')

        if User.query.filter_by(username=username).first():
            flash('Пользователь уже существует!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['score'] = 0
            session['current_question'] = 0
            session['answers'] = []
            session['start_time'] = datetime.now().isoformat()

            # Перемешиваем вопросы
            available_questions = QUESTIONS.copy() if len(QUESTIONS) >= QUESTIONS_PER_GAME else QUESTIONS
            selected_questions = random.sample(available_questions, min(QUESTIONS_PER_GAME, len(available_questions)))
            session['questions'] = selected_questions
            session['total_questions'] = len(selected_questions)

            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('quiz'))

        flash('Неверное имя пользователя или пароль!', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    if 'questions' not in session:
        return redirect(url_for('login'))

    questions = session['questions']
    current_q = session.get('current_question', 0)

    if current_q >= len(questions):
        return redirect(url_for('result'))

    if request.method == 'POST':
        selected_answer = int(request.form['answer'])
        correct_answer = questions[current_q]['correct']
        is_correct = (selected_answer == correct_answer)

        if is_correct:
            session['score'] = session.get('score', 0) + 1

        # Сохраняем ответ
        if 'answers' not in session:
            session['answers'] = []
        session['answers'].append({
            'question': questions[current_q]['question'],
            'selected': selected_answer,
            'correct': correct_answer,
            'is_correct': is_correct
        })

        session['current_question'] = current_q + 1
        return redirect(url_for('quiz'))

    # GET запрос
    question_data = questions[current_q]
    progress = int((current_q / len(questions)) * 100)

    return render_template('quiz.html',
                           question=question_data['question'],
                           options=question_data['options'],
                           question_num=current_q + 1,
                           total=len(questions),
                           progress=progress,
                           category=question_data.get('category', 'Общая'),
                           difficulty=question_data.get('difficulty', 'medium'))


@app.route('/result')
@login_required
def result():
    score = session.get('score', 0)
    total = session.get('total_questions', len(session.get('questions', [])))
    percentage = (score / total * 100) if total > 0 else 0
    rank = calculate_rank(percentage)

    # Сохраняем результат в БД
    quiz_result = QuizResult(
        user_id=current_user.id,
        score=score,
        total_questions=total,
        percentage=percentage
    )
    db.session.add(quiz_result)

    # Обновляем статистику пользователя
    current_user.total_games += 1
    current_user.total_score += score
    if score > current_user.best_score:
        current_user.best_score = score
    db.session.commit()

    # Сохраняем в текстовый файл
    save_stat_to_file(current_user.username, score, total, round(percentage, 1))

    # Получаем интересный факт
    fun_fact = get_fun_fact()

    # Получаем погоду в популярном туристическом городе
    try:
        weather_api = "https://api.open-meteo.com/v1/forecast?latitude=48.8566&longitude=2.3522&current_weather=true"
        weather_data = requests.get(weather_api, timeout=3).json()
        temperature = weather_data['current_weather']['temperature']
        weather_info = f"Погода в Париже сейчас: {temperature}°C"
    except:
        weather_info = "Загрузите погоду позже"

    # Лучшие результаты пользователя
    best_results = QuizResult.query.filter_by(user_id=current_user.id) \
        .order_by(QuizResult.score.desc()) \
        .limit(5).all()

    # Очищаем сессию, но сохраняем статистику для отображения
    session_data = {
        'score': score,
        'total': total,
        'percentage': round(percentage, 1),
        'rank': rank,
        'answers': session.get('answers', [])
    }

    return render_template('result.html',
                           score=score,
                           total=total,
                           percentage=round(percentage, 1),
                           rank=rank,
                           fun_fact=fun_fact,
                           weather=weather_info,
                           best_results=best_results,
                           answers=session_data['answers'])


@app.route('/profile')
@login_required
def profile():
    # Статистика пользователя
    total_games = current_user.total_games
    best_score = current_user.best_score
    avg_score = current_user.get_average_score()

    # История игр
    recent_results = QuizResult.query.filter_by(user_id=current_user.id) \
        .order_by(QuizResult.date_played.desc()) \
        .limit(10).all()

    return render_template('profile.html',
                           user=current_user,
                           total_games=total_games,
                           best_score=best_score,
                           avg_score=avg_score,
                           recent_results=recent_results)


@app.route('/leaderboard')
def leaderboard():
    # Топ-10 игроков по лучшим результатам
    top_players = db.session.query(User.username, User.best_score, User.total_games) \
        .order_by(User.best_score.desc()) \
        .limit(10).all()

    return render_template('leaderboard.html', top_players=top_players)


@app.route('/api/statistics')
@login_required
def api_statistics():
    """REST API для получения статистики"""
    results = QuizResult.query.filter_by(user_id=current_user.id).all()
    stats = calculate_statistics(results)

    return jsonify({
        'username': current_user.username,
        'statistics': stats,
        'total_games': current_user.total_games,
        'best_score': current_user.best_score,
        'average_score': current_user.get_average_score()
    })


@app.route('/reset_progress', methods=['POST'])
@login_required
def reset_progress():
    """Сброс прогресса пользователя"""
    QuizResult.query.filter_by(user_id=current_user.id).delete()
    current_user.total_games = 0
    current_user.total_score = 0
    current_user.best_score = 0
    db.session.commit()

    flash('Ваш прогресс был сброшен!', 'warning')
    return redirect(url_for('profile'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print(f"Загружено вопросов: {len(QUESTIONS)}")
        print("Сервер запущен на http://127.0.0.1:5000")
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import requests
import csv
from models import db, User, QuizResult
from utils import load_questions_from_csv, shuffle_questions_preserve_answers, shuffle_all_options

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-for-travel-quiz-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel_quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


def load_questions_from_csv(file_path):
    questions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for idx, row in enumerate(reader):
                correct_index = int(row['correct']) - 1  # Преобразуем 1-4 в 0-3
                print(f"Загружен вопрос {idx+1}: {row['question'][:50]}... правильный индекс: {correct_index} (вариант {row['correct']})")
                questions.append({
                    'id': idx,
                    'question': row['question'],
                    'options': [row['opt1'], row['opt2'], row['opt3'], row['opt4']],
                    'correct': correct_index,
                    'category': row.get('category', 'Общая'),
                    'difficulty': row.get('difficulty', 'medium')
                })
    except FileNotFoundError:
        print("Файл с вопросами не найден!")
        return []
    return questions


QUESTIONS = load_questions_from_csv('quiz_data.csv')
QUESTIONS_PER_GAME = 25


def shuffle_questions_preserve_answers(questions_list):
    shuffled = questions_list.copy()
    random.shuffle(shuffled)
    return shuffled


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Пользователь уже существует!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
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

            available_questions = QUESTIONS.copy() if len(QUESTIONS) >= QUESTIONS_PER_GAME else QUESTIONS

            shuffled_questions = shuffle_questions_preserve_answers(available_questions)

            selected_questions = shuffled_questions[:QUESTIONS_PER_GAME]

            selected_questions = shuffle_all_options(selected_questions)

            session['score'] = 0
            session['current_question'] = 0
            session['questions'] = selected_questions
            session['total_questions'] = len(selected_questions)
            session['answers_log'] = []

            for i, q in enumerate(selected_questions[:3]):
                print(f"Вопрос {i + 1}: правильный ответ теперь - {q['options'][q['correct']]}")

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

        current_question_data = questions[current_q]
        correct_answer = current_question_data['correct']
        is_correct = (selected_answer == correct_answer)

        print(f"\n{'=' * 50}")
        print(f"Вопрос {current_q + 1}: {current_question_data['question']}")
        print(f"Правильный ответ: {current_question_data['options'][correct_answer]}")
        print(f"Ответ пользователя: {current_question_data['options'][selected_answer]}")
        print(f"Результат: {'✅ ВЕРНО' if is_correct else '❌ НЕВЕРНО'}")
        print(f"{'=' * 50}\n")

        if is_correct:
            session['score'] = session.get('score', 0) + 1

        if 'answers_log' not in session:
            session['answers_log'] = []

        session['answers_log'].append({
            'question_num': current_q + 1,
            'question_text': current_question_data['question'],
            'selected_answer_text': current_question_data['options'][selected_answer],
            'correct_answer_text': current_question_data['options'][correct_answer],
            'is_correct': is_correct
        })

        session['current_question'] = current_q + 1
        return redirect(url_for('quiz'))

    question_data = questions[current_q]
    progress = int((current_q / len(questions)) * 100)

    return render_template('quiz.html',
                           question=question_data['question'],
                           options=question_data['options'],
                           question_num=current_q + 1,
                           total=len(questions),
                           progress=progress)


@app.route('/result')
@login_required
def result():
    score = session.get('score', 0)
    total = session.get('total_questions', len(session.get('questions', [])))
    percentage = (score / total * 100) if total > 0 else 0

    if percentage >= 90:
        rank = "🏆 Эксперт-путешественник"
    elif percentage >= 70:
        rank = "⭐ Опытный турист"
    elif percentage >= 50:
        rank = "🌍 Любознательный путешественник"
    else:
        rank = "📚 Начинающий турист"

    quiz_result = QuizResult(
        user_id=current_user.id,
        score=score,
        total_questions=total,
        percentage=percentage
    )
    db.session.add(quiz_result)

    current_user.total_games += 1
    current_user.total_score += score
    if score > current_user.best_score:
        current_user.best_score = score
    db.session.commit()

    with open('statistics.txt', 'a', encoding='utf-8') as f:
        f.write(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {current_user.username}: {score}/{total} ({percentage:.1f}%)\n")

    try:
        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en", timeout=5)
        if response.status_code == 200:
            fun_fact = response.json().get('text', '')
            fun_fact = f"✈️ {fun_fact[:150]}"
        else:
            fun_fact = "🌍 Путешествия расширяют кругозор!"
    except:
        fun_fact = "🌍 Путешествия расширяют кругозор!"

    best_results = QuizResult.query.filter_by(user_id=current_user.id) \
        .order_by(QuizResult.score.desc()) \
        .limit(5).all()

    answers_log = session.get('answers_log', [])

    return render_template('result.html',
                           score=score,
                           total=total,
                           percentage=round(percentage, 1),
                           rank=rank,
                           fun_fact=fun_fact,
                           best_results=best_results,
                           answers=answers_log)


@app.route('/profile')
@login_required
def profile():
    total_games = current_user.total_games
    best_score = current_user.best_score
    avg_score = current_user.get_average_score() if hasattr(current_user, 'get_average_score') else 0

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
    top_players = db.session.query(User.username, User.best_score, User.total_games) \
        .order_by(User.best_score.desc()) \
        .limit(10).all()

    return render_template('leaderboard.html', top_players=top_players)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print(f"\n{'=' * 50}")
        print(f"✅ СЕРВЕР ЗАПУЩЕН")
        print(f"📚 Загружено вопросов: {len(QUESTIONS)}")
        print(f"🌐 Адрес: http://127.0.0.1:5000")
        print(f"{'=' * 50}\n")
    app.run(debug=True)
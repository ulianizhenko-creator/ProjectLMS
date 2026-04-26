import random
import csv
from models import Question


def load_questions_from_csv(file_path):
    """Загрузка вопросов из CSV-файла"""
    questions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                questions.append({
                    'question': row['question'],
                    'options': [row['opt1'], row['opt2'], row['opt3'], row['opt4']],
                    'correct': int(row['correct']),
                    'category': row.get('category', 'Общая'),
                    'difficulty': row.get('difficulty', 'medium')
                })
    except FileNotFoundError:
        print("Файл с вопросами не найден!")
        return []
    return questions


def calculate_statistics(results):
    """Расчет статистики по результатам"""
    if not results:
        return {'average': 0, 'best': 0, 'total': 0}

    scores = [r.score for r in results]
    return {
        'average': round(sum(scores) / len(scores), 2),
        'best': max(scores),
        'total': len(results),
        'last_game': results[-1].date_played if results else None
    }


def get_random_questions(questions, count=10):
    """Получить случайные вопросы"""
    if len(questions) <= count:
        return random.sample(questions, len(questions))
    return random.sample(questions, count)


def get_questions_by_category(questions, category):
    """Фильтрация вопросов по категории"""
    return [q for q in questions if q.get('category') == category]


def format_date(date):
    """Форматирование даты"""
    if date:
        return date.strftime("%d.%m.%Y %H:%M")
    return "Нет данных"


def calculate_rank(percentage):
    """Определение ранга по проценту правильных ответов"""
    if percentage >= 90:
        return "🏆 Эксперт-путешественник"
    elif percentage >= 70:
        return "⭐ Опытный турист"
    elif percentage >= 50:
        return "🌍 Любознательный путешественник"
    elif percentage >= 30:
        return "📸 Начинающий турист"
    else:
        return "🗺️ Первооткрыватель"


def check_answer(selected, correct):
    """Проверка ответа"""
    return selected == correct


def save_stat_to_file(username, score, total, percentage):
    """Сохранение статистики в файл"""
    from datetime import datetime
    with open('statistics.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {username}: {score}/{total} ({percentage}%)\n")
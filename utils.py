import random
import csv
from datetime import datetime


def load_questions_from_csv(file_path):
    questions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for idx, row in enumerate(reader):
                correct_index = int(row['correct']) - 1
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


def shuffle_questions_preserve_answers(questions_list):
    shuffled = questions_list.copy()
    random.shuffle(shuffled)
    return shuffled


def shuffle_options_in_question(question):
    options = question['options']
    correct_index = question['correct']

    paired = [(opt, i == correct_index) for i, opt in enumerate(options)]

    random.shuffle(paired)

    new_options = [pair[0] for pair in paired]
    new_correct = [i for i, pair in enumerate(paired) if pair[1]][0]

    question['options'] = new_options
    question['correct'] = new_correct

    return question


def shuffle_all_options(questions_list):
    for question in questions_list:
        question = shuffle_options_in_question(question)
    return questions_list


def calculate_statistics(results):
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
    if len(questions) <= count:
        return random.sample(questions, len(questions))
    return random.sample(questions, count)


def get_questions_by_category(questions, category):
    return [q for q in questions if q.get('category') == category]


def format_date(date):
    if date:
        return date.strftime("%d.%m.%Y %H:%M")
    return "Нет данных"


def calculate_rank(percentage):
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
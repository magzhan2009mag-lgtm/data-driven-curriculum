# Кейс: Data-Driven Curriculum

Интеллектуальная система оценки эффективности учебников и учебных программ.
Проект для хакатона — делаем MVP.

## Задача
EdTech-платформа для методистов, которая:
1. Анализирует результаты тестирования школьников по отдельным темам учебной программы
2. Выявляет сложные для усвоения разделы
3. Сравнивает эффективность учебников
4. Формирует обоснованные рекомендации по распределению учебных часов

## Главная ценность
Переход от субъективных решений при выборе учебников и планировании часов
к решениям, основанным на измеримых образовательных результатах.

## Пользователь
Методист (не программист): интерфейс простой, на русском,
каждая рекомендация объясняется понятным текстом.

## Объём MVP (строго в этом порядке)
1. Генерация синтетических данных (скилл seed-data)
2. Метрики: сложность тем, сравнение учебников, рекомендации по часам (скилл metrics)
3. API на FastAPI
4. Дашборд на Next.js (скилл frontend-design)

НЕ делаем в MVP: авторизацию, загрузку файлов, PDF-экспорт, казахский язык.

## Стек
- Frontend: Next.js (app router), TypeScript, Tailwind, shadcn/ui, Recharts
- Backend: FastAPI (Python 3.11+), SQLAlchemy, pandas, scipy
- БД: SQLite (файл backend/data.db), без Docker
- Пакеты: npm (pnpm не используем), pip + requirements.txt

## Структура
- frontend/ — интерфейс
- backend/app/main.py — FastAPI
- backend/app/models.py — модели БД
- backend/app/analytics/ — все расчёты метрик
- backend/scripts/seed.py — генерация данных
- backend/tests/ — тесты

## Сущности
School, Class, Student, Textbook, Subject,
Topic(hours_planned), Test, TestResult(student, topic, textbook, score)

## API
- GET /topics/difficulty — сложность тем
- GET /textbooks/compare?topic_id= — сравнение учебников
- GET /recommendations — рекомендации по часам

## Команды
- backend: `cd backend && pip install -r requirements.txt`
- данные: `cd backend && python -m scripts.seed --reset`
- сервер: `cd backend && uvicorn app.main:app --reload` (порт 8000)
- тесты: `cd backend && pytest`
- frontend: `cd frontend && npm install && npm run dev` (порт 3000)
- линт: `cd frontend && npm run lint`

## Правила
- Все метрики считаются на бэкенде, фронт только отображает
- Сначала план (Plan mode), показать мне, потом код
- Работать по одному этапу, коммит после каждого
- Перед коммитом: тесты и линт проходят
- Интерфейс и тексты рекомендаций — на русском

## Скиллы проекта
- metrics — формулы и пороги аналитики
- seed-data — генерация синтетических данных
- demo — сценарий показа жюри
- frontend-design — стиль интерфейса
Отлично — теперь у нас уже есть все ключевые файлы проекта ✅
Ты попросил **переписать README нормально под твою текущую версию бота и Render-деплой**, без старых ошибок, упоминаний бесплатного Heroku и т.п.

Ниже — **готовый, актуальный README**, который ты можешь целиком вставить вместо текущего `README.md`.

---

## ✅ ГОТОВЫЙ README.md

Скопируй **всё полностью** и замени содержимое файла `README.md`.

````markdown
# Telegram AI Bot — Dushnilla

Телеграм-бот на базе **Telethon + FastAPI + OpenAI**.  
Работает 24/7 на **Render.com** как Web Service.

Бот поддерживает:
- диалоги с ИИ
- получение текущей даты и времени
- обработку изображений
- команды:
  - `/clear` — очистка истории
  - `/bash <cmd>` — запуск shell-команд
  - `/search <текст>` — поиск и краткое резюме
- контекст общения
- логирование работы

---

## Требования

- Python **3.10+**
- Telegram:
  - **API_ID**
  - **API_HASH**
  - **BOT TOKEN**
- **OpenAI API Key**
- Аккаунт **Render.com**

---

## Установка

### 1. Склонировать репозиторий

```bash
git clone <your_repo_url>
cd your_repo
````

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

---

## Настройка переменных окружения

Для локального запуска создай файл `.env`:

```env
OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxx
API_ID=1234567
API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BOTTOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

На Render эти значения добавляются в **Environment Variables**.

---

## Запуск локально

```bash
uvicorn src.main:app --host=0.0.0.0 --port=8080
```

Если запуск прошёл успешно:

* сервер будет доступен по `http://localhost:8080`
* бот подключится к Telegram

---

## Деплой на Render

### 1. Создай Web Service

В панели Render:

* **Runtime:** Python
* **Build Command:**

```bash
pip install -r requirements.txt
```

* **Start Command:**

```bash
uvicorn src.main:app --host=0.0.0.0 --port=${PORT:-8080}
```

---

### 2. Environment Variables

Добавь следующие переменные:

```
OPENAI_API_KEY
API_ID
API_HASH
BOTTOKEN
```

---

### 3. Доп. настройки

* **Health Check Path:** `/health`
* **PYTHON_VERSION:** `3.10.2`
* Auto-deploy по желанию

---

## Проверка работы

После старта Render:

* Сайт:
  `https://<your-app>.onrender.com`

* Проверка здоровья:

  ```
  /health
  ```

* Просмотр логов:

  ```
  /log
  ```

---

## Поддерживаемые команды

| Команда           | Описание                 |
| ----------------- | ------------------------ |
| Обычное сообщение | Диалог с ИИ              |
| `/clear`          | Очистка истории диалога  |
| `/search <тема>`  | Поиск + краткое резюме   |
| `/bash <cmd>`     | Выполнение команды shell |
| Отправка фото     | Анализ изображения ИИ    |

---

## Структура проекта

```
src/
 ├── main.py            # FastAPI + старт бота
 ├── bot/               # Telethon логика
 ├── handlers/          # Команды Telegram
 ├── functions/
 │    ├── chat_func.py
 │    └── additional_func.py
 └── utils/
      ├── utils.py
      └── __init__.py
```

---

## Диагностика проблем

### Бот не отвечает

Проверь:

✅ корректные ключи
✅ успешный коннект Telethon в логах
✅ статус `Your service is live` на Render
✅ отсутствие ошибок `ImportError` / `SyntaxError`

---

### Ошибки в логах

Все логи доступны по:

```
https://<your-app>.onrender.com/log
```

---

## Возможности для улучшения

* Добавить память пользователям (SQLite)
* Ограничить число запросов
* Добавить inline-кнопки
* Подключить vision-анализ изображений отдельно
* Подключить голосовые ответы

---

## Контакты

Проект поддерживается и расширяется под конкретные задачи.

---



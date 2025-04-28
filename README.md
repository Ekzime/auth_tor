```bash
app/
├── main.py
├── core/
│   ├── db.py           # подключение к БД
│   ├── config.py       # настройки проекта (токены, секреты)
│   └── security.py     # работа с JWT, паролями (хэширование, проверка)
├── models/
│   └── user.py
├── schemas/
│   └── user.py
├── services/
│   ├── db.py
│   ├── external_api.py
│   ├── auth.py         # логика авторизации
│   └── password_reset.py  # логика сброса пароля
├── routes/
│   ├── auth.py         # login, logout, register
│   └── password_reset.py # запрос сброса, подтверждение
├── utils/
│   └── email_sender.py # если потребуется отправлять письма
└── migrations/         # alembic миграции для БД
```
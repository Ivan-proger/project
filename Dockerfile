FROM python:3.12

WORKDIR /app

RUN apt-get update && apt-get install -y bash
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы приложения в рабочую директорию
COPY . /app

# Генерация SSL-сертификатов
RUN openssl genrsa -out webhook_pkey.pem 2048
RUN openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem -subj "/C=RU/ST=State/L=City/O=Organization/OU=Department/CN=yourdomain.com"


# Создание PostgreSQL-базы данных
#RUN su -c "psql -U postgres -c \"CREATE DATABASE mydatabase;\""

EXPOSE 5432
# Устанавливаем рабочую директорию для приложения
WORKDIR /app/tgBot
# Запускаем миграции и собираем статические файлы
#RUN python3 manage.py migrate

# Открываем порт 8000 для приложения
EXPOSE 8000
# Порт для вебхука
EXPOSE 8443

# Запуск Django-сервера и телеграм бота асинхроно
#CMD ["ls", "&&", "python3", "manage.py", "migrate","&&" "python3", "manage.py", "runserver","0.0.0.0:8000", "&&", "python3", "manage.py", "bot_asinc"]
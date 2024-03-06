import subprocess
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Запускает Django сервер и Telegram бота в параллельных процессах'

    def handle(self, *args, **options):
        # Запуск Django сервера
        subprocess.Popen(['python', 'manage.py', 'runserver'])

        # Запуск Telegram бота
        subprocess.Popen(['python', 'manage.py', 'bot_asinc'])

        # Ожидание завершения обоих процессов
        while True:
            pass
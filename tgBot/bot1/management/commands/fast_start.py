import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Запускает Django сервер и Telegram бота в параллельных процессах'

    def handle(self, *args, **options):
        # Запуск Django сервера
        subprocess.Popen([settings.APPEAL_PYTHON, 'manage.py', 'runserver'])

        # Запуск Telegram бота
        subprocess.Popen([settings.APPEAL_PYTHON, 'manage.py', 'bot_asinc'])

        # Ожидание завершения обоих процессов
        while True:
            pass
from django.apps import AppConfig


class Bot1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot1'

    def ready(self):
        import bot1.signals  # Подключаем файл с сигналами
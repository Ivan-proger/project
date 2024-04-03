import telebot
from django.core.management.base import BaseCommand
from django.conf import settings

bot = telebot.TeleBot(settings.BOT_TOKEN)
class Command(BaseCommand):
    help = "Tech bot"
    def handle(self, *args, **options):
        print("-=-=-=-=-=-=-=-=-=-=-\n\nЗапущены технические работы!!!\n\n-=-=-=-=-=-=-=-=-=-=-")

        @bot.message_handler(func=lambda message: True)
        def echo_all(message):
            bot.reply_to(message, "💔 Ведутся технические работы!")

        bot.polling()

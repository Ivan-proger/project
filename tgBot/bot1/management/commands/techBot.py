import os
import sys
import telebot
from django.core.management.base import BaseCommand
from django.conf import settings

bot = telebot.TeleBot(settings.BOT_TOKEN)
with open("admins_for_tex_wor.txt", "r", encoding="utf-8") as f:
    admins_text = f.read()
admins_list = admins_text.split()

class Command(BaseCommand):
    help = "Tech bot"
    def handle(self, *args, **options):
        print("-=-=-=-=-=-=-=-=-=-=-\n\nЗапущены технические работы!!!\n\n-=-=-=-=-=-=-=-=-=-=-")

        @bot.message_handler(commands=['work'])
        def help_func(message):
            if str(message.from_user.id) in admins_list:
                bot.send_message(message.chat.id, "Включаю основу...")
                # Запуск другой команды
                os.system(settings.APPEAL_PYTHON+" manage.py bot_asinc")
                # Завершение скрипта
                sys.exit()
        @bot.message_handler(func=lambda message: True)
        def echo_all(message):
            bot.reply_to(message, "💔 Ведутся технические работы!")

        bot.polling()

import telebot
from django.conf import settings

bot = telebot.TeleBot(settings.BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "💔 Ведутся технические работы!")

bot.polling()

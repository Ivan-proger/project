import telebot

bot = telebot.TeleBot("YOUR_BOT_TOKEN")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "💔 Ведутся технические работы!")

bot.polling()

"""
Django settings for tgBot project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path

from dotenv import load_dotenv
# Загружаем переменные из .env
load_dotenv()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")



# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


if DEBUG:
    ALLOWED_HOSTS = ["*"]

else:
    ALLOWED_HOSTS = []
#CSRF_TRUSTED_ORIGINS = ["https://..."]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
        # tg bot
    'bot1',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tgBot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tgBot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
CACHE_TTL = 60 * 60 * 5  # Время жизни кэша 5 часов

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'RU-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Как вызывать pyhton для выполнение команд
APPEAL_PYTHON = 'python'
# Вызовов ключевых функций бота до бана в секунду
MESSAGES_PER_SECOND = 4
#Bot messages:
WEBHOOK_WORK = False
BOT_TOKEN = os.getenv("BOT_TOKEN") # токен
BOT_TOKEN_TEST = os.getenv("BOT_TOKEN_TEST") # токен тест бота
CHANGE_DESIGN = True # Можно ли менять картинки оформления

try:
    with open("MESSAGE_START.txt", "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    with open("MESSAGE_START.txt", "w", encoding="utf-8") as f:
        f.write("""
<b>Приветствую тебя в мире аниме!</b> 🌸🎉
Я создан чтобы помочь тебе наслаждаться аниме, предоставляя возможность искать интересные тайтлы или выбирать из готового списка. 📺✨
Просто выбери `Поиск🔍` и отправь мне название аниме или воспользуйся списком, и я с радостью помогу тебе найти то, что ты ищешь! 🙌💫
Для списка команд введи /help. Приятного просмотра! 😊🌸""")
    with open("MESSAGE_START.txt", "r", encoding="utf-8") as f:
        content = f.read()
MESSAGE_START = content
 
ENJOY_WATCHING = 'Приятного просмотра :3'
# сообщение для списка сериалов
LIST_MESSAGE = '📁 Нажмите на понравившееся аниме \r\n│\r\n' 
CANCEL_MESSAGE = 'Отмена❌'
# если пользователь вводит некоректное значение
ERROR_VIDEO = f'🆘 Вы ввели некоректные значения, попробуйте еще раз или нажмите `{CANCEL_MESSAGE}` '
BAN_NESSAGE = '⛔Вам ограничили доступ за слишком частые запросы к боту\r\n <b>Попробуйте через пару минут еще раз</b> ' 
SEARCH_MESSAGE = f'🪄Вот что удалось найти! Вы можете еще раз задать новый поисковой запрос, если вы искали что-то другое или ввести `{CANCEL_MESSAGE}` для отмены поиска.'
try:
    with open("CONTACT_TS.txt", "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    with open("CONTACT_TS.txt", "w", encoding="utf-8") as f:
        f.write('Настройти контакт с поддержкой')
    with open("CONTACT_TS.txt", "r", encoding="utf-8") as f:
        content = f.read()
CONTACT_TS = content #фидбек от юзеров

if DEBUG:
    ADMIN_PANEL_URL = 'https://www.youtube.com/' #админка рабочий url обязательно
else:
    ADMIN_PANEL_URL = ALLOWED_HOSTS[0] + '/admin'

#количество эллементов в списке при выдаче всего доступного контена
ITEMS_PER_PAGE = 7 

try:
    with open("COMMAND_HELP.txt", "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    with open("COMMAND_HELP.txt", "w", encoding="utf-8") as f:
        f.write("Ответ на команду хелп")
    with open("COMMAND_HELP.txt", "r", encoding="utf-8") as f:
        content = f.read()
COMMAND_HELP = content + '\r\n' + CONTACT_TS

HELP_CHANNEL = '''
Разделитель "<code> ; </code>" (точка с запятой) с такими же 
  пробелами <b>C ДВУХ СТОРОН по одному пробелу</b>

При добавление видео :
 <i>-Первая строчка номер сезона
 -Вторая  строчка это название серии
 -Последняя строчка это названия(или его ID из бд) 
   cериала(аниме)в которое добавлять видео можно 
   писать просто id группы видосов</i>
 <i>-Также можно отвтеить на видео(в том же канале приватном)
   т.е. можно отправить видео когда бот не работает и потом
   просто ответить на это сообщение и бот все добавит в базу
   и</i> <b>СООБЩИТ ВАМ ОБ ЭТОМ!</b>
   <b>Как это сделать:</b>
        <i>-Ответить в итоге "repl" и тогда бот
         возьмет то что подписанно под видео

        -Заного написать все данные (также как
         для другого видео только в 
            сообщение-ответе)</i>
   
При добавление(обновление) постера к сериалу:
 <i>-Первая строчка названия сериала
 -Вторая строчка описание этого сериала</i>

Для чего режим кастомизации:
 "Start message" или "sm": 
   Добавление фото после команды /start через канал только
 "List message" или "lm": 
   Добавление фото к команде "Список аниме📋"
'''

KEYBOARD_CONFIG = {  #стартовая клавиатура
    "search_mode": {
        "title": "Поиск🔍", #что так или иначе увидит пользовтель
        "callback": "search_mode" #вызываемый метод из кода
    },
    "send_page": {
        "title": "Список аниме📋",
        "callback": "send_page"
    },
    "help": {
        "title": "Помощь🛟",
        "callback": "help"
    },
    "list_mode": {
        "title": "Подробный список📚",
        "callback": "list_mode"
    },
}
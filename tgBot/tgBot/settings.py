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
#Bot messages:
WEBHOOK_WORK = False
BOT_TOKEN = os.getenv("BOT_TOKEN") #токен
CHANGE_DESIGN = True # Можно ли менять картинки оформления
MESSAGE_START = '''
<b>Приветствую тебя в мире аниме!</b> 🌸🎉\r\n
Я создан чтобы помочь тебе наслаждаться аниме, предоставляя возможность искать интересные тайтлы или выбирать из готового списка. 📺✨\r\n
Просто выбери режим поиска и отправь мне название аниме или воспользуйся списком, и я с радостью помогу тебе найти то, что ты ищешь! 🙌💫\r\n
Для списка команд введи /help. Приятного просмотра! 😊🌸
''' 
SEARCH_VIDEO_TEXT ='🧩 <b>Найти определенную сeрию так: </b>\r\n{Номер сезона}<i>Пробел</i>{Номер серии} \r\nПример поиска: \r\n1 2' 
ENJOY_WATCHING = 'Приятного просмотра :3'
ERROR_VIDEO = '🆘 Вы ввели некоректные значения, попробуйте еще раз: ' #если пользователь вводит некоректное значение
LIST_MESSAGE = '📁 Нажмите на понравившееся аниме \r\n│\r\n' #сообщение для списка сериалов
CANCEL_MESSAGE = 'Отмена❌'
CONTACT_TS = 'настраивается в конфиге' #фидбек от юзеров
ADMIN_PANEL_URL = 'https://www.youtube.com/' #админка рабочий url обязательно
ITEMS_PER_PAGE = 7 #количество эллементов в списке при выдаче всего доступного контена
COMMAND_HELP = "Ответ на команду хелп"
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
         для другого видео только в сообщение-ответе)</i>
   
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
        "title": "Режим поиска🔍", #что так или иначе увидит пользовтель
        "callback": "search_mode" #вызываемый метод из кода
    },
    "send_page": {
        "title": "Список аниме📋",
        "callback": "send_page"
    },
    
}
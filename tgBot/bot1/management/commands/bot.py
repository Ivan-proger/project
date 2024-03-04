import time
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.conf import settings
from bot1.models import *
from fuzzywuzzy import fuzz

from telebot import TeleBot, types


# Объявление переменной бота
bot = TeleBot(settings.BOT_TOKEN, threaded=False)

#клавиатуры
main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
for key, value in settings.KEYBOARD_CONFIG.items():
    main_keyboard.add(types.KeyboardButton(value['title']))

cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel_keyboard.add(types.KeyboardButton(settings.CANCEL_MESSAGE)) 

keyboard_next_video_list = types.InlineKeyboardMarkup()
button = types.InlineKeyboardButton("Следующая страница ▶️", callback_data='next_list')
keyboard_next_video_list.row(button)

#ВЫЗОВ МЕТОДА НАСТРАИВАЕТСЯ В settings.KEYBOARD_CONFIG
def list_mode(message, start_index=0, end_index=25):
    all_series = Series.objects.all()[start_index:end_index]
    data_strings = [f'├ ▸<a href="t.me/{bot.get_me().username}?start={series.id}"> {series.name}</a> ◂' for series in all_series] # Создаем список строк, содержащих данные объектов Series   
    final_string = "\r\n".join(data_strings) # Объединяем строки в один конечный string формат
    count = Series.objects.count()
    if count > end_index:
        bot.send_message(message.chat.id, f'{settings.LIST_MESSAGE} {final_string} \r\n│\r\n└Показано  {end_index}/{count}', reply_markup=keyboard_next_video_list, parse_mode='HTML')
    else:
        keyboard_next_video_list_end = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("Это весь наш контен 👾", callback_data='no_work_date')
        keyboard_next_video_list_end.row(button)
        bot.send_message(message.chat.id, settings.LIST_MESSAGE + final_string, reply_markup=keyboard_next_video_list_end, parse_mode='HTML')  


def search_series(message, query=None):
    if message.text != settings.CANCEL_MESSAGE:
        if query == None:
            query = message.text
        series = Series.objects.all()
        best_matches = []

        for s in series:
            similarity = fuzz.token_sort_ratio(s.name, query)
            if similarity > 70:                             #настраиваемый коэфицент
                best_matches.append((s, similarity))
            
        if best_matches:
            best_matches = sorted(best_matches, key=lambda x: x[1], reverse=True)
            obj = Series.objects.get(name=[match[0] for match in best_matches][0])

            video_counts = Video.objects.values('series_id', 'season').annotate(num_videos=Count('id'))
            text_msg_season = ''
            for video_count in video_counts:
                if Series.objects.get(id=video_count['series_id']).name == obj.name:
                    text_msg_season += f'- сезон {video_count['season']}: Кол-во серий {video_count['num_videos']}\r\n'
            keyboard_start = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("✨ Первая серия >", callback_data=f'start_watching-{obj.id}')
            keyboard_start.row(button)
            try:
                bot.send_photo(message.chat.id, obj.poster,
                            caption= str("⚡️ Название: " + obj.name + "\r\n" + 
                                        "Описание: " + obj.description + "\r\n" + text_msg_season), reply_markup=keyboard_start)
            except:
                bot.send_message(message.chat.id, "⚡️ Название: " + obj.name + "\r\n" + 
                                                "Описание: " + obj.description + "\r\n" + text_msg_season, reply_markup=keyboard_start)
            
            msg_video = bot.send_message(message.chat.id, settings.SEARCH_VIDEO_TEXT ,reply_markup=cancel_keyboard)
            bot.register_next_step_handler(msg_video, search_video, obj.id)

        else:
            if query.strip().isdigit():
                if len(query.split()) == 1:
                    try:
                        obj = Series.objects.get(id=int(query))
                        video_counts = Video.objects.values('series_id', 'season').annotate(num_videos=Count('id'))
                        text_msg_season = ''
                        for video_count in video_counts:
                            if Series.objects.get(id=video_count['series_id']).name == obj.name:
                                text_msg_season += f'- сезон {video_count['season']}: {video_count['num_videos']} видео \r\n'
                        keyboard_start = types.InlineKeyboardMarkup()
                        button = types.InlineKeyboardButton("Первая серия ▶️", callback_data=f'start_watching-{obj.id}')
                        keyboard_start.row(button)
                        try:
                            bot.send_photo(message.chat.id, obj.poster,
                                        caption= str("⚡️ Название: " + obj.name + "\r\n" + 
                                                    "Описание: " + obj.description + "\r\n" + text_msg_season), reply_markup=keyboard_start)
                        except:
                            bot.send_message(message.chat.id, "⚡️ Название: " + obj.name + "\r\n" + 
                                                            "Описание: " + obj.description + "\r\n" + text_msg_season, reply_markup=keyboard_start)
                        msg_video = bot.send_message(message.chat.id, settings.SEARCH_VIDEO_TEXT ,reply_markup=cancel_keyboard)
                        bot.register_next_step_handler(msg_video, search_video, obj.id)      
                    except:
                        msg = bot.send_message(message.chat.id, "🚫 Нет совпадений, попробуйте еще раз:", reply_markup=cancel_keyboard)
                        bot.register_next_step_handler(msg, handle_next_search_input)
                else:
                    msg = bot.send_message(message.chat.id, "🚫 Нет совпадений, попробуйте еще раз:", reply_markup=cancel_keyboard)
                    bot.register_next_step_handler(msg, handle_next_search_input)
            elif len(query.split('_')) == 3:
                text_list = query.split('_')
                text_list.pop(0)
                search_video(message, int(query.split('_')[0]), text_list)                              
            else:                           
                msg = bot.send_message(message.chat.id, "🚫 Нет совпадений, попробуйте еще раз:", reply_markup=cancel_keyboard)
                bot.register_next_step_handler(msg, handle_next_search_input)    
    else:
        bot.send_message(message.chat.id, "🚫 Поиск отменен.", reply_markup=main_keyboard)

def handle_next_search_input(message):
    if message.text == settings.CANCEL_MESSAGE:
        bot.send_message(message.chat.id, "🚫 Поиск отменен.", reply_markup=main_keyboard)
    else:
        search_series(message)

def search_mode(message):
    msg = bot.send_message(message.chat.id, "🔍 Вы выбрали режим поиска.", reply_markup=cancel_keyboard)
    bot.register_next_step_handler(msg, search_series)

def search_video(message, series_id, text_list=None):  
    if text_list == None:
        text = message.text
        text_list = text.split()

    if message.text == settings.CANCEL_MESSAGE:
        bot.send_message(message.chat.id, "🚫 Поиск отменен.", reply_markup=main_keyboard)
    else:
        if len(text_list) == 2 and all(part.isdigit() for part in text_list):
            try:
                obj_video = Video.objects.get(series_id=series_id,season=text_list[0] ,number=text_list[1])

                keyboard_next_video = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("▶️ Следующая серия", callback_data='next_video')
                keyboard_next_video.row(button)
                button_share = types.InlineKeyboardButton("📢 Поделится", 
                    switch_inline_query=f'{settings.REFERRAL_MESSAGE} t.me/{bot.get_me().username}?start={series_id}_{obj_video.season}_{obj_video.number}')
                keyboard_next_video.row(button_share)

                bot.send_video(message.chat.id, obj_video.video_id,reply_markup=keyboard_next_video ,
                               caption=f'({obj_video.id}) Сезон {obj_video.season}, cерия №{obj_video.number}, {obj_video.name}')
                bot.send_message(message.chat.id, settings.ENJOY_WATCHING , reply_markup=main_keyboard)
            except:
                bot.send_message(message.chat.id, settings.ERROR_VIDEO, reply_markup=main_keyboard)            
        else:
            for key, value in settings.KEYBOARD_CONFIG.items():
                if message.text == value['title']:
                    callback = value['callback']
                    globals()[callback](message)
                    return 
            if message.text.split()[0] == '/start' and len(message.text.split()) > 1:
                text = message.text.split()[1]
                bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                search_series(message, text)
            else:    
                bot.send_message(message.chat.id, settings.ERROR_VIDEO, reply_markup=main_keyboard)   

#----ТИИПА ОДИН МЕТОД :/ ---

#обработчик инлайн клавиатуры
@bot.callback_query_handler(func=lambda call: True)
def handle_video_button_click(call):
    if call.message.video:
        # Проверяем, что произошло нажатие на кнопку к видео
        if call.data == 'next_video':
            obj = Video.objects.get(id=int(call.message.caption.split('(')[1].split(')')[0]))
            try:
                try:
                    obj1 = Video.objects.get(number=obj.number+1, season=obj.season, series_id = obj.series_id)
                    keyboard_next_video = types.InlineKeyboardMarkup()
                    button = types.InlineKeyboardButton("▶️ Следующая серия", callback_data='next_video')
                    keyboard_next_video.row(button)
                    button_share = types.InlineKeyboardButton("📢 Поделится", 
                        switch_inline_query=f'{settings.REFERRAL_MESSAGE} t.me/{bot.get_me().username}?start={obj1.series_id}_{obj1.season}_{obj1.number}')
                    keyboard_next_video.row(button_share)

                    bot.send_video(call.message.chat.id, obj1.video_id,reply_markup=keyboard_next_video ,caption=f'({obj1.id}) Сезон {obj1.season}, cерия №{obj1.number}, {obj1.name}')
                    bot.send_message(call.message.chat.id, settings.ENJOY_WATCHING , reply_markup=main_keyboard)
                except:
                    obj1 = Video.objects.get(number=1, season=obj.season+1)
                    bot.send_video(call.message.chat.id, obj1.video_id,reply_markup=keyboard_next_video ,caption=obj1.name)
                    bot.send_message(call.message.chat.id, settings.ENJOY_WATCHING , reply_markup=main_keyboard)
            except:
                bot.send_message(call.message.chat.id,'Это было последнее видеo😢', reply_markup=main_keyboard)   
    if call.data == 'next_list':
        list1 = call.message.text.split('/')
        list1 = list1[0].split()
        start = list1[len(list1)-1]
        list_mode(call.message, int(start), int(start)+25)
    
    if call.data.split('-')[0] == 'start_watching':
        obj = Series.objects.get(id=int(call.data.split('-')[1]))
        search_video(call.message, int(call.data.split('-')[1]), text_list=['1', '1'])
    
    if call.data.split('-')[0] == 'add':
        if Users.objects.filter(external_id=int(call.data.split('-')[1]), is_superuser=True):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, f"Введите кол-во юзеров({str(Users.objects.count())}) для получения сообщения: (Введите любую букву для отмены)")
            bot.register_next_step_handler(call.message, admin_range_user)
    if call.data == 'cancel':
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
#админ команды
@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    if Users.objects.filter(external_id=message.from_user.id, is_superuser=True):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        button = types.InlineKeyboardButton("Админ панель", url=settings.ADMIN_PANEL_URL)
        button1 = types.InlineKeyboardButton("Написать рекламаный пост", callback_data=f'add-{message.from_user.id}')
        button2 = types.InlineKeyboardButton("Закрыть ❌", callback_data='cancel')
        keyboard.add(button, button1, button2)     
        bot.send_message(message.from_user.id, 'Админ панель', reply_markup=keyboard)
    else:
        bot.send_message(message.from_user.id, f'за покупкой рекламы > {settings.CONTACT_TS}', reply_markup=main_keyboard, parse_mode='HTML')
    bot.delete_message(message.chat.id, message.message_id)

def admin_range_user(message):
    if message.text.isdigit():
        bot.send_message(message.chat.id, f'Выбранное колличество: {message.text}, введите клавиатуру <code>Название_кнопки : url; </code>:', parse_mode='HTML')
        bot.register_next_step_handler(message,admin_keyboard_post, message.text)
    else:
        bot.send_message(message.from_user.id, settings.CANCEL_MESSAGE)
        handle_admin_command(message)

def admin_keyboard_post(message, range_send):
    keyboard = types.InlineKeyboardMarkup(row_width=1)  # создаем объект клавиатур
    if ':' in message.text:
        try:
            buttons_data = message.text.split('; ')  # разбиваем строку на отдельные кнопки и их данные
            for button in buttons_data:
                button_text, button_url = button.split(' : ')  # делим данные кнопки на текст и ссылку
                keyboard.add(types.InlineKeyboardButton(text=button_text, url=button_url.strip()))  # добавляем кнопку в клавиатуру

                bot.send_message(message.chat.id, 'Введите текст рекламы(Для использования отдельных шрифтов используйте HTML разметку телеграмма): ')
                bot.register_next_step_handler(message, admin_confirmation, range_send, keyboard)# отправляем ответ с клавиатурой
        except:
            bot.send_message(message.chat.id, 'Введенный Url не может проверить телеграмм, возможны ошибки в ссылке, отправка остановлена ❌')
    else:
        bot.send_message(message.chat.id, "Сообщение будет существовать без клавиатуры")
        bot.send_message(message.chat.id, 'Введите текст рекламы: ')
        bot.register_next_step_handler(message, admin_confirmation, range_send, keyboard)

def admin_confirmation(message, range_send, keyboard):
    bot.send_message(message.chat.id, message.text, reply_markup=keyboard, parse_mode='HTML')
    bot.send_message(message.chat.id, 'Подтвердите отправку набрав "<code>Yes</code>"', parse_mode='HTML')
    bot.register_next_step_handler(message, admin_post, range_send, keyboard, message.text)

def admin_post(message, range_send, keyboard, text):
    if message.text == 'Yes' or message.text == 'yes':
        count = 0
        if int(range_send) > 0:
            random_records = list(Users.objects.all().order_by('?')[:int(range_send)])
            for obj in random_records:
                try:
                    time.sleep(0.2)
                    bot.send_message(str(obj.external_id), text, reply_markup=keyboard)
                    count += 1
                except:
                    print(f'Пользователя - {str(obj.external_id)} не существует в базе')
            bot.send_message(message.chat.id, f'Сообщение отправлено: {count} пользователям')
        else:
            list_us = list(Users.objects.all().order_by('?'))
            for obj in list_us:
                try:
                    time.sleep(0.2) #Для отпрпавки надо некоторое время
                    bot.send_message(str(obj.external_id), text, reply_markup=keyboard)
                    count += 1
                except:
                    print(f'Пользователя - {str(obj.external_id)} не существует в базе')
            bot.send_message(message.chat.id, f'Сообщение отправлено(всем возможным): {count} людям')
    else:
        bot.send_message(message.chat.id,'Отправка остановлена ❌') 


class Command(BaseCommand):
    help = 'Telegram bot.'       

    def handle(self, *args, **kwargs):
        bot.enable_save_next_step_handlers(delay=2) # Сохранение обработчиков
        bot.load_next_step_handlers()	# Загрузка обработчиков 

        #добавляения юзеров в бд
        @bot.message_handler(commands=['start'])
        def start(message):
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            u, c = Users.objects.get_or_create(external_id = message.from_user.id, defaults={'name': message.from_user.username,})

            if " " in message.text:
                text = message.text.split()[1]
                search_series(message, text)
            else:
                bot.send_message(message.from_user.id, settings.MESSAGE_START, reply_markup=main_keyboard, parse_mode='HTML')

        @bot.message_handler(content_types=['text'])
        def work(message):
            for key, value in settings.KEYBOARD_CONFIG.items():
                if message.text == value['title']:
                    callback = value['callback']
                    globals()[callback](message)
                    return 


        #Добавления сериала и видео к нему с помощью приватного канала
        @bot.channel_post_handler(content_types=['video', 'text', 'photo'])
        def addBDfilm(message):
            Channel.objects.get_or_create(id_channel=message.chat.id) #добавления канала в базу
            id = Channel.objects.get(id_channel=message.chat.id) #получение строки из канала

            if id.is_super_channel:
                if message.content_type == "video":
                    id_video = message.video.file_id
                    message_text = message.caption    
                    if message_text:                        
                        message_text_list = message_text.split(' ; ')
                        s, _ = Series.objects.get_or_create(name = message_text_list[3])  
                                                           #последняя строчка это названия cериала(аниме) в которое добавлять видео
                        video = Video.objects.create(
                            series = s,
                            video_id = id_video,
                            season = message_text_list[0], #первая строчка номер сезоня
                            number = message_text_list[1], #вторая сстрочка до " ; " номер серии
                            name =  message_text_list[2],  #третья  строчка это название серии
                        )
                        video.save()
                        bot.send_message(message.chat.id, f'Видео успешно добавлено! \r\n{video.name}, к сериалу: <code>{s.name}</code>', parse_mode='HTML')
                if message.content_type == "photo":
                    id_photo = message.photo[0].file_id
                    message_text_photo = message.caption
                    message_text_list = message_text_photo.split(' ; ')
                    s, cre = Series.objects.get_or_create(
                        name = message_text_list[0],          #первая строчка названия сериала
                        defaults={
                          'poster':  id_photo,
                          'description': message_text_list[1] #вторая строчка описание этого сериала
                        })
                    bot.send_message(message.chat.id, f'Успешно добавлен сериал \r\nимя: <code>{s.name}</code> \r\nОписание: {s.description}', parse_mode='HTML')
    
                    if not cre:
                        s.poster = id_photo
                        s.description = message_text_list[1]
                        s.save()
                        bot.send_message(message.chat.id, f'Успешно добавлен сериал \r\nимя: <code>{s.name}</code> \r\nОписание: {s.description}', parse_mode='HTML')

        bot.infinity_polling() 
        						


    
import os
import sys
import requests
import asyncio #база для асинхроной работы бота
import telebot #база бота нашего
import matplotlib.pyplot as plt #пострение графика активности
import io #для работы с байтами 
import datetime # Модуль для работы с временем

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.conf import settings
from asgiref.sync import sync_to_async # способ работы в асинхронном режими Djabgo ORM запросов
from django.core.cache import cache # Кэшируем базу

from bot1.models import * # импорт всех моделей Django

from fuzzywuzzy import fuzz # модуль для поиска с ошибками
from aiofiles import open as aio_open  # Import for async file operations
from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot, types, ExceptionHandler
from telebot.asyncio_storage import StateMemoryStorage # способ храниения состояний пользователей
from telebot.asyncio_handler_backends import State, StatesGroup # состояния


# включение/выключение дебага в settings.py
if settings.DEBUG:
    import logging #дебаг режим
    logger = telebot.logger
    telebot.logger.setLevel(logging.DEBUG)  # Outputs debug messages to console.
    class MyExceptionHandler(ExceptionHandler):
        async def handle(self, exception):
            logger.error(exception)

    bot = AsyncTeleBot(settings.BOT_TOKEN_TEST, state_storage=StateMemoryStorage(), exception_handler=MyExceptionHandler())
else:
    bot = AsyncTeleBot(settings.BOT_TOKEN, state_storage=StateMemoryStorage())

# FSM
class MyStates(StatesGroup):
    search_series = State()
       # admin states
    admin_keybord_add_set = State()
    admin_quantity_users = State()
    admin_text_add = State()
    admin_confirmation = State()
    admin_changing_variables = State()

# клавиатуры
main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_board = []
for key, value in settings.KEYBOARD_CONFIG.items():
    main_board.append(types.KeyboardButton(value['title']))
main_keyboard.add(*main_board)

cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel_keyboard.add(types.KeyboardButton(settings.CANCEL_MESSAGE)) 



# обновление последней активности
async def update_activity(external_id, need_user=False):
    try:
        user = await sync_to_async(lambda: Users.objects.get(external_id=external_id))()
        current_date = timezone.now()
        last_activity = user.last_activity 
        if last_activity.day != current_date.day: #Собираем статистику уникальных пользователей за день
            try:
                # Получение записи по текущей дате
                service_usage = await sync_to_async(lambda: ServiceUsage.objects.get(date=current_date))()
            except ServiceUsage.DoesNotExist:
                # Если записи нет, создаем новую и устанавливаем счетчик на 1
                service_usage = ServiceUsage(date=current_date, count=0)
            finally:
                # Если запись уже существует, увеличиваем счетчик на 1
                service_usage.count += 1
                await service_usage.asave()      
        await user.update_last_activity()
        if user.is_ban:
            return False       
        else:
            if need_user:
                return user
            else:
                return True
    except:
        pass        

 # проверка на подписку
async def subscription_check(message):
    user = await sync_to_async(lambda: Users.objects.get(external_id=message.chat.id))()   
    if user.is_subscription == True:    # проверка на подписку на рекламные каналы
        return True
    else:
        keyboard_ads = types.InlineKeyboardMarkup()
        channels = await sync_to_async(lambda: list(Channel.objects.filter(id_advertising=True)))()
        i = 0                    
        for channel in channels:
            i += 1
            keyboard_ads.add(types.InlineKeyboardButton(text=f"Канал №{i}", url=f"https://t.me/{channel.name_channel}"))
        if i != 0:
            keyboard_ads.add(types.InlineKeyboardButton(text=f"▫ Проверить подписки ▫", callback_data=f"check_subscription"))
            await bot.send_message(message.chat.id, "Подпишись", reply_markup=keyboard_ads)
        else:
            user.is_subscription = True
            await user.asave()
            return True
    return False


# список всех сериалов
async def all_items():
    # Получить список всех сериалов из кэша
    all_series = cache.get('all_series')
    # Если данные в кэше отсутствуют, загрузить их из базы данных
    if all_series is None:
        all_series = await sync_to_async(lambda: list(Series.objects.filter(is_release=True)))()
        cache.set('all_series', all_series, settings.CACHE_TTL)
    return all_series
# Отправка картинки
async def send_page(message):
    await bot.delete_message(message.chat.id, message.id)
    if os.path.exists('ListMessageID.txt'):
        with open('ListMessageID.txt', "r") as f:
            file_id = f.readline().strip()
            msg = await bot.send_photo(message.chat.id, file_id)
    else:
        msg = await bot.send_message(message.chat.id, settings.LIST_MESSAGE, parse_mode="HTML")
    await send_page1(msg)
# Функция для отправки сообщения с клавиатурой
async def send_page1(message, current_page=1):
    # Кэшируем чтобы не думать!
    keyboard = cache.get(f'send_page-{current_page}')
    if keyboard is None:
        # Определяем индексы элементов текущей страницы
        items = await all_items()
        start_index = (current_page - 1) * settings.ITEMS_PER_PAGE
        end_index = min(start_index + settings.ITEMS_PER_PAGE, len(items))
        
        # Создаем клавиатуру
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for item in items[start_index:end_index]:
            # Добавляем кнопку для каждого элемента на текущей странице
            keyboard.add(types.InlineKeyboardButton(text=f"{item.name}", callback_data=f"series_{item.id}"))
        
        # Добавляем кнопки для навигации по страницам
        prev_button = types.InlineKeyboardButton(text="◀️Назад", callback_data=f"prevpage_{current_page}")
        next_button = types.InlineKeyboardButton(text="Вперед▶️", callback_data=f"nextpage_{current_page}")
        page_info = types.InlineKeyboardButton(text=f"{current_page}/{await get_total_pages(len(items))}", callback_data="page_info")
        keyboard.row(prev_button, page_info, next_button)
        # Создаем кэш
        cache.set(f'send_page-{current_page}', keyboard, settings.CACHE_TTL)
        
    # Отправляем сообщение с клавиатурой и информацией о текущей странице
    await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id, reply_markup=keyboard)
# Функция для вычисления общего количества страниц
async def get_total_pages(total_items=None):
    if total_items == None:
        total_items = len(await all_items())
    return (total_items + settings.ITEMS_PER_PAGE - 1) // settings.ITEMS_PER_PAGE

async def search_mode(message):
    await bot.send_message(message.chat.id, "🔍 Вы выбрали режим поиска.", reply_markup=cancel_keyboard)
    await bot.set_state(message.from_user.id, MyStates.search_series, message.chat.id)

# Поиск сериала
async def search_obj_series(query):
    # Получаем кэш
    series = await all_items()
    # Если запрос - это число, ищем по id
    if str(query).isdigit():
        for series_id in series:
            if series_id.id == int(query):
                return series_id

    # Иначе, используем fuzzywuzzy для поиска по имени
    query = str(query)
    if series:
        # фильтруем по нашей схожести равной 50
        filtered_series = [item for item in series if fuzz.ratio(item.name, query) >= 50]
        if not filtered_series:
            filtered_series = [item for item in series if query in item.description]
            if not filtered_series:
                filtered_series = [item for item in series if fuzz.ratio(item.description, query) >= 20]
        # Если найден только один объект, возвращаем его
        if len(filtered_series) == 1:
            return filtered_series[0]
        # Если найдено несколько объектов, возвращаем объект с наивысшим коэффициентом схожести
        best_match = max(filtered_series, key=lambda x: fuzz.ratio(x.name, query), default=None) 
        if best_match == None:
            max(filtered_series, key=lambda x: fuzz.ratio(x.description, query), default=None)
        return best_match   
    return False

# Ответ на помощь
async def help(message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await bot.send_message(message.chat.id, settings.COMMAND_HELP)   
    await bot.delete_state(message.from_user.id, message.chat.id)

async def list_mode(message, start_index=0, end_index=36, user=None, all_series=None): 
    if not all_series: # Если мы не вызываем метод уже с готовым листом сериалов
        if not user:
            user = await update_activity(message.chat.id)# обновление последней активности
        if user:
            # Получаем все сериалы из метода по определенному ренджу
            all_series = (await all_items())[start_index:end_index]
            if start_index == 0:
                reply_text = settings.LIST_MESSAGE
            # Чтобы без лишних слов сразу все выдало 
            else:
                reply_text = ''        
    else:
        reply_text = "🔥 Самое популярное 🔥 \r\n\r\n"
        user = True
    # Проверка на бан юзера   
    if user:
        async def generate_string(all_series, username):
            final_string = ''
            for series in all_series:
                # Создаем собственно текст и ссылки для пользователей
                if len(series.description.split()) <= 1:
                    final_string += f'  ▸<a href="t.me/{username}?start=Serias_{series.id}"> {series.name}</a> ◂'
                elif len(series.description) < 75:
                    final_string += f'  ▸<a href="t.me/{username}?start=Serias_{series.id}"> {series.name}</a> ◂ —  <i>{series.description}</i>'
                else:
                    final_string += f'  ▸<a href="t.me/{username}?start=Serias_{series.id}"> {series.name}</a> ◂ — <i>{series.description[:75]}...</i>'
                final_string += "\r\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖\r\n"
            return final_string

        # Проверяем кэш есть ли уже такая страница там:
        if reply_text != "🔥 Самое популярное 🔥 \r\n\r\n":
            final_string = cache.get(f'final_string-{end_index}')
            if final_string is None:
                final_string = await generate_string(all_series, (await bot.get_me()).username)
                cache.set(f'final_string-{end_index}', final_string, settings.CACHE_TTL)
        else:
            final_string = cache.get(f'final_string-hot')
            if final_string is None:
                final_string = await generate_string(all_series, (await bot.get_me()).username)
                cache.set(f'final_string-hot', final_string, settings.CACHE_TTL)
            await bot.send_message(message.chat.id, reply_text + final_string, parse_mode='HTML')
            # Выходим если мы просто хотели список популярного
            return None
        
        # Считаем количество сериалов
        count = cache.get('Series.count')
        if count is None:
            count = await sync_to_async(Series.objects.count)()
            # Устанавливаем кэш если его нету
            cache.set('Series.count', count, settings.CACHE_TTL)

        if count > end_index:
            keyboard_next_video_list = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Следующая страница ▶️", callback_data='next_list')
            keyboard_next_video_list.row(button)
            # Отправляем если есть еще невыведенные сериалы
            await bot.send_message(message.chat.id, 
                f'{reply_text} {final_string} \r\n│\r\n└Показано  {end_index}/{count}', 
                reply_markup=keyboard_next_video_list, parse_mode='HTML'
                )
        else:
            await bot.send_message(message.chat.id, reply_text + final_string, parse_mode='HTML')
    else:
        await bot.send_message(message.chat.id, settings.BAN_NESSAGE, reply_markup=main_keyboard, parse_mode='html')

class Command(BaseCommand):
    help = 'Async Telegram bot.'       

    
    def add_arguments(self, parser):
        # Добавляем дополнительные аргументы
        parser.add_argument(
            '--webhook',
            action='store_true',
            help='Webhook for tg bot'
        )

    def handle(self, *args, **options):
        print("\n--- Bot runing ---\n")
        # Если при запуске передать webhook
        if options['webhook']:
            settings.WEBHOOK_WORK = True

        # Воздух свежи перед: GOVNOCODE = ON

        # обработчик инлайн клавиатуры
        @bot.callback_query_handler(func=lambda call: True)
        async def handle_button_click(call):
            try:
                user = await update_activity(call.message.chat.id, True)
                if user: # обновление последней активности
                    if call.data == 'next_list':
                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                        list1 = call.message.text.split('/')
                        list1 = list1[0].split()
                        start = list1[len(list1)-1]
                        # Отправляем следующий список
                        await list_mode(call.message, int(start), int(start)+25, user)

                    if call.data.split('-')[0] == 'start_watching': # Первая серия под сериалом
                        await bot.delete_state(call.message.chat.id, call.message.chat.id)
                        await search_video(call.message, id_series=int(call.data.split('-')[1]), season=1, number=1)
                    if call.data.split("_")[0] == 'season':
                        id_series = call.data.split("_")[1]
                        number_season = call.data.split("_")[2]
                        number_video = int(call.data.split("_")[3])
                        keyboard = types.InlineKeyboardMarkup(row_width=4)
                        keyboard.row(types.InlineKeyboardButton('Выберите нужну серию:', callback_data='None'))
                        list_video = []
                        for i in range(1, number_video+1):
                            list_video.append(types.InlineKeyboardButton(i, callback_data=f'video_{id_series}_{number_season}_{i}'))
                        keyboard.add(*list_video)
                        keyboard.row(types.InlineKeyboardButton('◀️ Вернуться назад', callback_data=f'backSeries_{id_series}'))
                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)
                    if call.data.split("_")[0] == 'video':
                        number_season = call.data.split("_")[2]
                        number_video = call.data.split("_")[3]
                        await bot.delete_state(call.message.chat.id, call.message.chat.id)
                        await search_video(call.message, id_series=int(call.data.split('_')[1]), season=number_season, number=number_video)
                    if call.data.split('_')[0] == 'backSeries':
                        series_id = call.data.split('_')[1]
                        keyboard = types.InlineKeyboardMarkup(row_width=2)
                        # Получаем кэш
                        season_row = cache.get(f'season_row-{series_id}')
                        if season_row is None:
                            season_row = []
                            videos = await sync_to_async(lambda: list(Video.objects.filter(series_id=series_id) \
                                .values('series_id') \
                                .annotate(num_videos=Count('id')) \
                                .values('series_id', 'season','num_videos')))()

                            for video_count in videos:
                                season_row.append(types.InlineKeyboardButton(
                                    f'Сезон {video_count['season']}', 
                                    callback_data = f'season_{series_id}_{video_count['season']}_{video_count['num_videos']}'
                                    ))
                            cache.set(f'season_row-{series_id}', season_row, settings.CACHE_TTL)
                        keyboard.add(*season_row)
                        keyboard.row(types.InlineKeyboardButton(
                            '📢 Поделится', 
                            url=f'https://t.me/share/url?url=t.me/{(await bot.get_me()).username}?start=Serias_{series_id}')
                            )
                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)  
                        
                    # Популярное                                         
                    if call.data == 'hot_series':
                        current_date = timezone.now().replace(day=1)
                        # Кэш
                        list_series = cache.get('hot_series')
                        # Если данные в кэше отсутствуют, загрузить их из базы данных
                        if list_series is None:
                            # Делаем запрос на самые популярные id сериалов
                            series_ids = await sync_to_async(
                                lambda: list(
                                    SeriesUsage.objects.filter(date=current_date)\
                                        .order_by('-count')[:5]\
                                            .values_list('series_id',
                                                          flat=True
                                                        )
                                )
                            )()      
                            # Передаем список популярных сериалов в саму модель сериалов      
                            list_series = await sync_to_async(lambda: list(Series.objects.filter(id__in=series_ids)))()
                            cache.set('hot_series', list_series, 60*30) # На 30 минут кэш
                        # Выводим пользователю список 
                        await list_mode(call.message, all_series=list_series)

                    # Обрабатываем нажатие на кнопку "Назад"
                    if call.data.startswith("prevpage"):
                        current_page = int(call.data.split("_")[1])
                        if int(current_page) > 1:
                            await send_page1(call.message, current_page - 1)
                    # Обрабатываем нажатие на кнопку "Далее"
                    elif call.data.startswith("nextpage"):
                        current_page = int(call.data.split("_")[1])
                        if int(current_page) < await get_total_pages():
                            await send_page1(call.message, current_page + 1)
                    if call.data.startswith("series"):
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        await search_series(call.message, await search_obj_series(call.data.split("_")[1]), user)

                    # проверка на подписку
                    if call.data == 'check_subscription':
                        user = await sync_to_async(lambda: Users.objects.get(external_id=call.message.chat.id))()
                        channels = await sync_to_async(lambda: list(Channel.objects.filter(id_advertising=True)))()
                        i=0
                        for channel in channels:
                            x = await bot.get_chat_member(channel.id_channel, user.external_id)
                            if x.status == "member" or x.status == "creator" or x.status == "administrator":
                                i += 1
                        if i == len(channels) or user.is_superuser == True:
                            user.is_subscription = True
                            # Обновляем статистику пришедших к каналу юзеров
                            channels = await sync_to_async(lambda: list(Channel.objects.filter(id_advertising=True)))()
                            for channel in channels:
                                channel.subscribers_added += 1
                                await channel.asave()
                            await bot.delete_message(call.message.chat.id, call.message.id)
                            await bot.send_message(call.message.chat.id, "Все ограничения сняты✅, нажимте на кнопки ниже для пользования нашим сервисом!🤗")
                            await user.asave()
                        else:
                            await bot.answer_callback_query(callback_query_id=call.id, text='Вы не подписались❌')

                    # Дальше админ команды и т.д.
                    if call.message.video:
                        # Проверяем, что произошло нажатие на кнопку к видео
                        if call.data.split('-')[0] == 'next_video':
                            if await subscription_check(call.message):
                                inline_keyboard = call.message.reply_markup
                                if inline_keyboard.keyboard:
                                    if inline_keyboard.keyboard[0]:
                                        inline_keyboard.keyboard[0].pop(0)  # Удаляем первую кнопку
                                        # Редактируем сообщение с обновленной инлайн клавиатурой
                                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=inline_keyboard)
                                # Назначаем
                                season = call.data.split('-')[2]
                                series_id = call.data.split('-')[1]
                                number = call.data.split('-')[3]
                                # Устанавливаем кэш
                                list_season = cache.get(f'season-{season}-{series_id}')
                                if not list_season:
                                    list_season = await sync_to_async(lambda: list(Video.objects.filter(season=season, series_id=series_id)))()
                                    cache.set(f'season-{season}-{series_id}', list_season, settings.CACHE_TTL)
                                else:
                                    obj_video = None
                                    # Проще перебрать чем что то еще 
                                    for video in list_season:
                                        # Сверяем что в куче кэша етсь то что нам надо (а точнее видео на номер выше)
                                        if str(video.season) == str(season) and str(video.number) == str(int(number)+1):
                                            obj_video = video
                                            await search_video(call.message, obj_video=obj_video)
                                            break
                                    # Ну если нет такого то делаем запрос на первую серию следующего сезона
                                    if not obj_video:
                                        await search_video(call.message, id_series=series_id, season=int(season)+1, number=1)


                    # Закрытие панельки
                    if call.data == 'cancel':
                        await bot.delete_message(call.message.chat.id, call.message.message_id)

                    # Чистим кэш
                    if call.data == 'cacheclear':
                        cache.clear()
                        await bot.answer_callback_query(callback_query_id=call.id, text='Кэш очищен🚮')
                        await bot.delete_message(call.message.chat.id, call.message.message_id)

                    # Релиз сериалов
                    if call.data == 'premiere':
                        await bot.delete_message(call.message.chat.id, call.message.message_id)
                        all_series = await sync_to_async(lambda: list(Series.objects.filter(is_release=False)))()
                        text = '— — — — — — — — — — — — — —\r\n'
                        for series in all_series:
                            series.is_release = True
                            await series.asave()
                            text += f'✅Выпущен — <code>{series.name}</code>\r\n— — — — — — — — — — — — — —\r\n'
                        await bot.send_message(call.message.chat.id, text, parse_mode='HTML')

                    # Закрытия сообщения и очистка статы
                    if call.data == 'cancelState':
                        await bot.delete_message(call.message.chat.id, call.message.message_id)
                        await bot.delete_state(call.message.chat.id, call.message.chat.id)
                    if call.data.split('-')[0] == 'add':
                        if await sync_to_async(lambda: list(Users.objects.filter(external_id=int(call.data.split('-')[1]), is_superuser=True).all()))():
                            await bot.delete_message(call.message.chat.id, call.message.message_id)
                            await bot.send_message(call.message.chat.id, 
                                f'Введите клавиатуру так: \r\n<code>Название_кнопки - url </code>:', 
                                reply_markup=cancel_keyboard, parse_mode='HTML')
                            await bot.set_state(call.message.chat.id, MyStates.admin_keybord_add_set, call.message.chat.id)

                    # обнуления рекламной подписки для всех пользователей
                    if call.data == 'reset_is_subscription':
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        users = await sync_to_async(lambda: list(Users.objects.all().defer('name', 'last_activity', 'ref_code')))()
                        # Обновляем значение поля is_subscription на False для каждого объекта
                        for user in users:
                            user.is_subscription = False
                            await user.asave()
                        await bot.send_message(call.message.chat.id, "✅Все пользователи снова будут проверяться на подписку рекламных каналов!")

                    # Создания и отправка графика
                    if call.data == 'graf': 
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        # Вычисляем дату, которая находится за 31 деньми до текущей даты
                        start_date = datetime.date.today() - datetime.timedelta(days=31)
                        # Получить все даты и все значения
                        all_dates = await sync_to_async(lambda: list(ServiceUsage.objects.filter(date__gte=start_date).values_list('date', flat=True)))()
                        all_values = await sync_to_async(lambda: list(ServiceUsage.objects.filter(date__gte=start_date).values_list('count', flat=True)))()
                        # Преобразуем даты в формат день-месяц для отображения на графике
                        short_dates = [date.strftime('%d-%m') for date in all_dates]
                        plt.bar(range(len(all_values)), all_values, edgecolor='black', color='pink')
                        # Устанавливаем короткие даты на оси X
                        plt.xticks(range(len(all_values)), short_dates, rotation=45)
                        plt.grid(axis='y', linestyle='--', linewidth=1)
                        plt.title("Статистика посещений пользователями за 31 день:")
                        plt.ylabel("Количество уникальных пользователей")
                        plt.gca().set_facecolor('#D3D3D3')  
                        # Сохраняем график в байтовый объект
                        buffer = io.BytesIO()
                        plt.savefig(buffer, format='png')
                        buffer.seek(0) #читаем файл сначала чтобы все отправилось в тг

                        await bot.send_photo(call.message.chat.id, photo=buffer, caption="🔝Статистика уникального использования за 31 день🔝")
                        plt.close()
                        buffer.close()

                    # Создаем файл с ID пользователей    
                    if call.data == 'fail_txt_bd':
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        
                        async def write_file(users, filename):
                            async with aio_open(filename, 'w') as file:
                                async for user in users:
                                    await file.write(f'{user.external_id}\n')
                        # Отправляем его
                        async def send_file(bot, chat_id, filename):
                            with open(filename, 'rb') as file:
                                await bot.send_document(chat_id, file, caption=f'Список пользователей ({timezone.now().strftime("%Y-%m-%d %H:%M:%S")})')

                        users = await sync_to_async(lambda: Users.objects.all().defer('name', 'last_activity', 'ref_code'))()
                        filename = 'users.txt'
                        await write_file(users, filename)
                        await send_file(bot, call.message.chat.id, filename)
                    # Изменение оформления да/нет
                    if call.data == 'CHANGE_DESIGN':
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        if settings.CHANGE_DESIGN:
                            settings.CHANGE_DESIGN = False
                        else:
                            settings.CHANGE_DESIGN = True
                        await handle_admin_command(call.message, True)

                    # Технические работы включение
                    if call.data == 'tex_work':
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        keyboard = types.InlineKeyboardMarkup(row_width=2)
                        buttonx = types.InlineKeyboardButton(" нет ❌ ", callback_data='cancel')
                        buttonY = types.InlineKeyboardButton(" да, точно ✅", callback_data='tex_working')
                        keyboard.add(buttonY, buttonx)                
                        await bot.send_message(
                            call.message.chat.id,
                            "🆘 Вы точно уверенны???\r\n<b>Это может привести к выключению бота</b>",
                            reply_markup=keyboard,
                            parse_mode='HTML'
                        )
                    if call.data == 'tex_working':
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        list_admins = await sync_to_async((lambda: list(Users.objects.filter(is_superuser=True))))()
                        list_admins_text = []
                        with open("admins_for_tex_wor.txt", "w", encoding="utf-8") as f:
                            for admin in list_admins:
                                f.write(str(admin.external_id))
                                list_admins_text.append(f'\r\n- @{str(admin.name)}')
                        text = ''.join(*list_admins_text)
                        await bot.send_message(
                            call.message.chat.id,
                            f"<b>Включён режим технических работ!\r\nАдмины для разморозки тех работ:{text} \r\n#техработы</b>",
                            parse_mode='HTML'
                            )        
                        # Запуск другой команды
                        os.system(settings.APPEAL_PYTHON+" manage.py techBot")
                        # Завершение скрипта
                        sys.exit()
                    # Изминение текстовых констат 
                    if call.data == 'text_const':
                        await bot.delete_message(call.message.chat.id, call.message.id)
                        keyboard = types.InlineKeyboardMarkup(row_width=2)
                        variables_list={'settings.MESSAGE_START' : 'Сообщение /start' , 
                                        'settings.CONTACT_TS' : 'Контакт тех.под.',
                                        'settings.COMMAND_HELP' : 'Ответ на /help',
                                        }
                        for key, value in variables_list.items():
                            keyboard.add(types.InlineKeyboardButton(value, callback_data=f'const-{key}'))
                        keyboard.add(types.InlineKeyboardButton(" -- Закрыть ❌ -- ", callback_data='cancel'))
                        await bot.send_message(
                            call.message.chat.id,
                            "|<b> Будьте крайне осторожны изменяя эти параметры! </b>|",
                            reply_markup=keyboard,
                            parse_mode='HTML'
                            )
                    if call.data.startswith("const"):
                        key = call.data.split('-')[1]
                        keyboard = types.InlineKeyboardMarkup()
                        buttontext = types.InlineKeyboardButton(" Вы хотетие изменить ее значение? ", callback_data='None')
                        buttonx = types.InlineKeyboardButton(" нет ❌ ", callback_data='cancel')
                        buttonY = types.InlineKeyboardButton(" да, точно ✅", callback_data=f'change-{key}')
                        keyboard.add(buttontext) 
                        keyboard.row(buttonY, buttonx)                    
                        await bot.send_message(
                            call.message.chat.id,
                            f"Данные переменной <code>{key.split('.')[1]}</code>: \r\n{str(eval(key))}",
                            reply_markup=keyboard,
                            parse_mode='HTML'
                            )
                    if call.data.split('-')[0] == 'change':
                        keyboard = types.InlineKeyboardMarkup(row_width=2)
                        keyboard.add(types.InlineKeyboardButton(f"Нажмите чтобы отменить❌", callback_data='cancelState'))
                        await bot.set_state(call.message.chat.id, MyStates.admin_changing_variables, call.message.chat.id)
                        async with bot.retrieve_data(call.message.chat.id, call.message.chat.id) as data:
                            data['changing_variable'] = call.data.split('-')[1]
                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=keyboard)
                        await bot.send_message(call.message.chat.id, 'Введите новое значение: ', reply_markup=cancel_keyboard)
                    if call.data == 'MESSAGES_PER_SECOND':
                        count = settings.MESSAGES_PER_SECOND
                        keyborad = types.InlineKeyboardMarkup()
                        button0 = types.InlineKeyboardButton(f'Сейчас лимит: {count}', callback_data="None")
                        buttonPlus = types.InlineKeyboardButton(f'🟢Добавить', callback_data="PLUS")
                        buttonMinus = types.InlineKeyboardButton(f'🔴Уменьшить', callback_data="MINUS")
                        buttonx = types.InlineKeyboardButton(" -- Закрыть ❌ -- ", callback_data='cancel')
                        keyborad.row(button0) 
                        keyborad.row(buttonMinus, buttonPlus)
                        keyborad.row(buttonx)
                        await bot.send_message(call.message.chat.id,
                        ''' 
                        'Изменить допустимое число сообщений которые может отправить пользователь в секунду боту 
                        (при перезагрузке бота вернеться к сток занчению) применять при ддос атаках на бота'
                        ''', 
                        reply_markup=keyborad)
                    if call.data == 'PLUS':
                        settings.MESSAGES_PER_SECOND += 1
                        count = settings.MESSAGES_PER_SECOND
                        keyborad = types.InlineKeyboardMarkup()
                        button0 = types.InlineKeyboardButton(f'Сейчас лимит: {count}', callback_data="None")
                        buttonPlus = types.InlineKeyboardButton(f'🟢Добавить', callback_data="PLUS")
                        buttonMinus = types.InlineKeyboardButton(f'🔴Уменьшить', callback_data="MINUS")
                        buttonx = types.InlineKeyboardButton(" -- Закрыть ❌ -- ", callback_data='cancel')
                        keyborad.row(button0) 
                        keyborad.row(buttonMinus, buttonPlus)
                        keyborad.row(buttonx)
                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyborad) 
                    if call.data == 'MINUS':
                        settings.MESSAGES_PER_SECOND -= 1
                        count = settings.MESSAGES_PER_SECOND
                        keyborad = types.InlineKeyboardMarkup()
                        button0 = types.InlineKeyboardButton(f'Сейчас лимит: {count}', callback_data="None")
                        buttonPlus = types.InlineKeyboardButton(f'🟢Добавить', callback_data="PLUS")
                        buttonMinus = types.InlineKeyboardButton(f'🔴Уменьшить', callback_data="MINUS")
                        buttonx = types.InlineKeyboardButton(" -- Закрыть ❌ -- ", callback_data='cancel')
                        keyborad.row(button0) 
                        keyborad.row(buttonMinus, buttonPlus)
                        keyborad.row(buttonx)
                        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyborad)                                                
                else:
                    await bot.send_message(call.message.chat.id, settings.BAN_NESSAGE, reply_markup=main_keyboard, parse_mode='html')
            except Exception as e:
                if settings.DEBUG:
                    import traceback #дебаг
                    logger.error(f'\n\n{traceback.format_exc()}\n\n')
                else:
                    await bot.send_message(call.message.chat.id, f'😨 Произошла ошибка! введите <code>/start</code>', parse_mode='HTML')
                    

#-\-\-\-\-\-\-\-\--\-\-\-\-\-\-\-\-\-\--\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--\-\-\-\-\-\-\- конец логигики колбек сообщений


        #Отмена всех состояний
        @bot.message_handler(state="*", text=asyncio_filters.TextFilter(equals=settings.CANCEL_MESSAGE))
        async def any_state(message):
            await bot.delete_message(message.chat.id, message.id)
            await bot.send_message(message.chat.id, settings.CANCEL_MESSAGE, reply_markup=main_keyboard)
            await bot.delete_state(message.from_user.id, message.chat.id)

        @bot.message_handler(commands=['help'])   # ответ на команду /help
        async def help_func(message):
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.send_message(message.chat.id, settings.COMMAND_HELP)

        # Ответ на команду /start а также все что с ней связано (рефералка и выдача по реф системе)
        @bot.message_handler(commands=['start'])
        async def start(message):
            user, created = await sync_to_async(Users.objects.get_or_create)(
                external_id=message.from_user.id,
                defaults={'name': message.from_user.username,}
            )
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

            # Отправка приветсвия с фотографией либо без если файл отсуствует 
            async def send_start_message(message):
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton('Популярное аниме🔥', callback_data='hot_series'))
                if os.path.exists('StartMessageID.txt'):
                    with open('StartMessageID.txt', "r") as f:
                        file_id = f.readline().strip()
                        await bot.send_photo(message.chat.id, file_id, settings.MESSAGE_START, reply_markup=keyboard, parse_mode="HTML")

                else:
                    await bot.send_message(message.chat.id, settings.MESSAGE_START, reply_markup=keyboard, parse_mode="HTML")
            # Если пользователь впервые 
            if created: 
                # Создаем либо возращаем на то сколько пришло к боту просто от команды /start
                statistic_code, _ = await sync_to_async(lambda: StatisticRef.objects.get_or_create(name_code='local'))()
                statistic_code.user_sdded += 1
                await statistic_code.asave()  
                # Ставь рефералку того что юзер просто использовал бота без рефки
                user.ref_code = 'local'
                await user.asave()  

                await bot.send_message(message.chat.id, 'Обязательно ознакомся с нашим функционалом!', reply_markup=main_keyboard, parse_mode='html')
            else:
                user.name = message.from_user.username
                await user.asave()

    
            # Если пользователь передал еще код рефералки
            if " " in message.text:
                # выдача сериала или серии по запросу в /start 
                text = message.text.split()[1]
                # Рефералка
                if text.split('_')[0] == 'ref':
                    if not user.ref_code:
                        code = text.split('_')[1]
                        user.ref_code = code
                        await user.asave()
                        try:
                            # Получение записи
                            code_usage = await sync_to_async(lambda: StatisticRef.objects.get(name_code=code))()
                        except StatisticRef.DoesNotExist:
                            # Если записи нет, создаем новую и устанавливаем счетчик на 1
                            code_usage = StatisticRef(name_code=code, user_sdded=1)
                            await code_usage.asave()
                        else:
                            # Если запись уже существует, увеличиваем счетчик на 1
                            code_usage.count += 1
                            await code_usage.asave()
                            await bot.send_message(message.chat.id, "Обязательно ознакомся с нашим функционалом!", reply_markup=main_keyboard)

                    else:
                        await bot.send_message(message.chat.id, f"У вас уже имеется реферальный код - <code>{user.ref_code}</code>", parse_mode='HTML')
                else:
                    if text.split('_')[1].isdigit and not len(text.split('_')) == 3 and text.split('_')[0] == 'Serias':
                        await search_series(message, await search_obj_series(int(text.split('_')[1])), user)
                    elif len(text.split('_')) == 3:
                        text_list = text.split('_')
                        obj_series = await search_obj_series(int(text_list[0]))
                        if obj_series:
                            await search_video(message, id_series=int(text_list[0]), season=int(text_list[1]), number=int(text_list[2]))
                        else:
                            await bot.send_message(message.chat.id, settings.ERROR_VIDEO)
            else:
                await send_start_message(message) 
        
        # Функциия админки изменение текстовых констант 
        @bot.message_handler(state=MyStates.admin_changing_variables)
        async def sawp_text(message):
            if message.text.casefold() != 'отмена':
                async with bot.retrieve_data(message.chat.id, message.chat.id) as data:
                    key = data['changing_variable']
                    text = message.text
                    exec(f"{key} = '''\n{text}\n'''")
                    with open(f"{key.split('.')[1]}.txt", "w", encoding="utf-8") as f:
                        f.write(text)
                    await bot.send_message(message.chat.id, 
                        f"Новые данные переменной <code>{key.split('.')[1]}</code>: \r\n{str(eval(key))}",parse_mode='HTML',reply_markup=main_keyboard
                        )
                await bot.delete_message(message.chat.id, message.id)
                await bot.delete_state(message.from_user.id, message.chat.id)
            else:
                await any_state(message)

        # Поиск конкретного сериала  ---- core состовляющая
        @bot.message_handler(state=MyStates.search_series)
        async def search_series(message, obj=None, user=None):
            if not user:
                user = await update_activity(message.chat.id, True) # обновление последней активности 
            if user:         
                if not obj:
                    obj = await search_obj_series(message.text)
                    if obj:
                        await bot.send_message(message.chat.id, settings.SEARCH_MESSAGE, parse_mode='html')
                if obj:                      
                    # Если наш юзер еще не смотрел этот сериал то ставим на просмотрено
                    series_user = await sync_to_async(lambda: list(user.series.all()))()
                    if not obj in series_user:
                        await user.series.aadd(obj)
                        current_date = timezone.now().replace(day=1)
                        try:                       
                            # Получение записи по текущей дате
                            series_usage = await sync_to_async(lambda: SeriesUsage.objects.get(series=obj,date=current_date))()
                        except SeriesUsage.DoesNotExist:
                            # Если записи нет, создаем новую и устанавливаем счетчик на 0
                            series_usage = SeriesUsage(series=obj, date=current_date, count=0)
                        finally:
                            # Если запись уже существует, увеличиваем счетчик на 1
                            series_usage.count += 1
                            await series_usage.asave() 
                    # Организация и выдача сериала пользователю 
                    series_id = obj.id
                    keyboard_start = types.InlineKeyboardMarkup(row_width=2)
                    # Получаем кэш
                    season_row = cache.get(f'season_row-{series_id}')
                    text_msg_season = cache.get(f'text_msg_season-{series_id}')
                    if season_row is None:
                        # Формируем запрос для получения всех видео по series_id с уникальным season
                        videos = await sync_to_async(lambda: list(Video.objects.filter(series_id=series_id) \
                            .values('series_id') \
                            .annotate(num_videos=Count('id')) \
                            .values('series_id', 'season','num_videos')))()
                        text_msg_season = ''
                        season_row = []
                        # Если всего один сезон то выдаем серии
                        if len(videos) == 1:
                            videos2 = await sync_to_async(lambda: list(Video.objects.filter(series_id=series_id)))()
                            for i in videos2:
                                season_row.append(types.InlineKeyboardButton('Фильм №'+str(i.number), callback_data=f'video_{str(series_id)}_{str(i.season)}_{str(i.number)}'))  
                            text_msg_season += f"   ▪ Cезон {videos[0]['season']}: серий {videos[0]['num_videos']}\r\n"                      
                        else:
                            for video_count in videos:
                                season_row.append(
                                    types.InlineKeyboardButton(
                                    f'Сезон {video_count['season']}', 
                                    callback_data = f'season_{series_id}_{video_count['season']}_{video_count['num_videos']}'
                                    ))                                
                                text_msg_season += f"   ▪ Cезон {video_count['season']}: серий {video_count['num_videos']}\r\n"
                        # Формируем кэш 
                        print(f'\n\n{season_row}\n\n') 
                        cache.set(f'season_row-{series_id}', season_row, settings.CACHE_TTL)
                        cache.set(f'text_msg_season-{series_id}', text_msg_season, settings.CACHE_TTL)
                    
                    button = types.InlineKeyboardButton("✨ Смотреть первую серию >", callback_data=f'start_watching-{series_id}')
                    keyboard_start.row(button)
                    keyboard_start.add(*season_row)
                    keyboard_start.row(types.InlineKeyboardButton('📢 Поделится', url=f'https://t.me/share/url?url=t.me/{(await bot.get_me()).username}?start=Serias_{series_id}'))

                    try:
                        await bot.send_photo(
                            message.chat.id, 
                            obj.poster,
                            caption= str(f"⚡️ <b>{obj.name}</b>\r\n<i>{obj.description}</i>\r\n\r\n{text_msg_season}"),
                            reply_markup=keyboard_start,
                            parse_mode='HTML'
                            )
                    except:
                        await bot.send_message(
                            message.chat.id,
                            f"⚡️ <b>{obj.name}</b>\r\n<i>{obj.description}</i>\r\n{text_msg_season}",
                            reply_markup=keyboard_start,
                            parse_mode='HTML'
                            )
                        
                else:
                    await bot.send_message(message.chat.id, settings.ERROR_VIDEO)  
            else:
                await bot.delete_state(message.chat.id, message.chat.id)
                await bot.send_message(message.chat.id, settings.BAN_NESSAGE, reply_markup=main_keyboard, parse_mode='html')

        # Поиск видо как после сериала так и как отдельный метод для вызова где угодно
        async def search_video(message, id_series=None, season=None, number=None, obj_video=None):
            if await update_activity(message.chat.id): # обновление последней активности 
                try:
                    if not obj_video:
                        # КЭШ КЭШ КЭШ
                        list_season = cache.get(f'season-{season}-{id_series}')
                        if not list_season:
                            list_season = await sync_to_async(lambda: list(Video.objects.filter(season=season, series_id=id_series)))()
                            cache.set(f'season-{season}-{id_series}', list_season, settings.CACHE_TTL)
                            obj_video = await sync_to_async(lambda: Video.objects.get(series_id=id_series,season=season,number=number))()  
                        else:
                            # Проще перебрать чем что то еще 
                            for video in list_season:
                                if str(video.season) == str(season) and str(video.number) == str(number):
                                    obj_video = video
                                    break

                    keyboard_next_video = types.InlineKeyboardMarkup()
                    button = types.InlineKeyboardButton("Следующая серия ▶️", callback_data=f'next_video-{obj_video.series_id}-{obj_video.season}-{obj_video.number}')
                    keyboard_next_video.row(button)
                    # Создание ссылки поделится
                    button_share = types.InlineKeyboardButton(
                        "📢 Поделится", 
                        url=f'https://t.me/share/url?url=t.me/{(await bot.get_me()).username}?start={obj_video.series_id}_{obj_video.season}_{obj_video.number}'
                        ) 
                    keyboard_next_video.row(button_share)

                    await bot.send_video(
                        message.chat.id, 
                        obj_video.video_id,
                        reply_markup=keyboard_next_video ,
                        caption=f'📺 <b>{obj_video.name}</b> \r\n  Сезон {obj_video.season}, cерия №{obj_video.number}', 
                        supports_streaming=True, 
                        parse_mode="html"
                        )
                    await bot.send_message(message.chat.id, settings.ENJOY_WATCHING , reply_markup=main_keyboard)
                    await bot.delete_state(message.chat.id, message.chat.id)
                except:
                    await bot.send_message(message.chat.id, 'Возможно такой серии не существует😢')
            else:
                await bot.delete_state(message.chat.id, message.chat.id)
                await bot.send_message(message.chat.id, settings.BAN_NESSAGE, reply_markup=main_keyboard, parse_mode='html')


        # Админ команды
        @bot.message_handler(commands=['admin'])
        async def handle_admin_command(message, red=False):
            if await sync_to_async(lambda: list(Users.objects.filter(external_id=message.from_user.id, is_superuser=True).all()))() or red:
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                button = types.InlineKeyboardButton("💌Веб панель", url=settings.ADMIN_PANEL_URL)
                button1 = types.InlineKeyboardButton("✏️Написать рекламаный пост", callback_data=f'add-{message.from_user.id}')
                button2 = types.InlineKeyboardButton("🔄Обновить проверку на подписку", callback_data=f'reset_is_subscription')
                button3 = types.InlineKeyboardButton("📊График активности юзеров", callback_data=f'graf')
                button4 = types.InlineKeyboardButton("🗂Выгрузить базу.txt Telegram ID", callback_data=f'fail_txt_bd')
                if settings.CHANGE_DESIGN:
                    button5 = types.InlineKeyboardButton("🎨Выключить режим оформления", callback_data=f'CHANGE_DESIGN')
                else:
                    button5 = types.InlineKeyboardButton("🎨Включить режим оформления", callback_data=f'CHANGE_DESIGN')
                button6 = types.InlineKeyboardButton("🧑‍💻Включить режим тех. работ", callback_data=f'tex_work')
                button7 = types.InlineKeyboardButton("👾Изменения текстовых констант", callback_data=f'text_const')
                button8 = types.InlineKeyboardButton("🤖Количество запросов в сек. для юзеров", callback_data=f'MESSAGES_PER_SECOND')
                button9 = types.InlineKeyboardButton("👁️Релиз контента", callback_data=f'premiere')
                button10 = types.InlineKeyboardButton("🗑Очистить кэш", callback_data=f'cacheclear')
                buttonx = types.InlineKeyboardButton(" -- Закрыть ❌ -- ", callback_data='cancel')
                keyboard.add(button, button1, button2, button3, button4, button5, button6, button7, button8, button9, button10,buttonx)     
                await bot.send_message(message.chat.id, '💌💌💌--Админ панель--💌💌💌', reply_markup=keyboard)
            else:
                await bot.send_message(message.from_user.id, f'За покупкой рекламы > {settings.CONTACT_TS}', reply_markup=main_keyboard, parse_mode='HTML')
            if not red:
                await bot.delete_message(message.chat.id, message.message_id)
        # Создание клавиатуру для рекламы
        @bot.message_handler(state=MyStates.admin_keybord_add_set)
        async def admin_keybord_add(message):
            keyboard = types.InlineKeyboardMarkup()  # создаем объект клавиатур
            if message.text:
                try:
                    for button_text in message.text.split('\n'):
                        if ';' in button_text:
                            current_row = []
                            button_texts = button_text.split(' ; ')
                            for button_text in button_texts:
                                button_name, button_url = button_text.split(' - ')
                                current_row.append(types.InlineKeyboardButton(text=button_name, url=button_url))
                            keyboard.row(*current_row)
                        else:
                            button_name, button_url = button_text.split(' - ')
                            keyboard.add(types.InlineKeyboardButton(text=button_name, url=button_url))
                    
                        print(button_url.strip())
                    await bot.send_message(
                        message.chat.id, 
                        'Введите текст(вы можете добавить фото или видео) рекламы(Для использования отдельных шрифтов используйте HTML разметку телеграмма): '
                        )
                    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                        data['admin_keyboard_add'] = keyboard
                    await bot.set_state(message.from_user.id, MyStates.admin_text_add, message.chat.id)
                except:
                    await bot.send_message(message.chat.id, 'Введенный Url не может проверить телеграмм, возможны ошибки в ссылке, попробуйте еще раз: ')
            else:
                await bot.send_message(message.chat.id, "Сообщение будет существовать без клавиатуры.\r\nВведите текст(вы можете добавить фото или видео) рекламы: ")
                async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                    data['admin_keyboard_add'] = keyboard
                await bot.set_state(message.from_user.id, MyStates.admin_text_add, message.chat.id)            

        @bot.message_handler(content_types=['video', 'text', 'photo'], state=MyStates.admin_text_add)
        async def admin_text_add_only_text(message):
            async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['admin_message_id'] = message.id
            await bot.set_state(message.from_user.id, MyStates.admin_quantity_users, message.chat.id)
            await bot.send_message(message.chat.id, 'Сообщение добавлено! \r\nВведите количество получателей либо любую букву, для отправке всем.')

        @bot.message_handler(state=MyStates.admin_quantity_users)
        async def admin_quantity_users_add(message):
            if str(message.text).isdigit():
                async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                    data['admin_quantity_users'] = message.text
                await bot.send_message(message.chat.id, f'Отлично! \r\nОтправим {message.text} чел.')
            else:
                async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                    data['admin_quantity_users'] = 0
                await bot.send_message(message.chat.id, 'Число не действительно, будет отправлнно всем юзерам бота.')
            try:
                await bot.set_state(message.from_user.id, MyStates.admin_confirmation, message.chat.id)
                async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                    await bot.copy_message(message.chat.id, message.chat.id, data['admin_message_id'], reply_markup=data['admin_keyboard_add']) 
                await bot.send_message(message.chat.id, 'Верно? \r\nДля отправки введите `<code>Yes</code>`: ', parse_mode="HTML")     
            except Exception as e:
                 await bot.send_message(message.chat.id, f'⛔⛔⛔ Ошибка: \r\n<code>{e}</code>', parse_mode="HTML")
                 await any_state(message)

        @bot.message_handler(state=MyStates.admin_confirmation)
        async def admin_confirmation_add(message):
            if message.text == 'Yes' or message.text == 'yes':
                await bot.send_message(message.chat.id, 'запускаю шарманку', reply_markup=main_keyboard)
                async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                    if data['admin_quantity_users'] != 0:
                        # Oпределенный рэндж рассылки
                        records = await sync_to_async(lambda: list(Users.objects.all().order_by('?').defer('name', 'last_activity', 'ref_code')[:int(data['admin_quantity_users'])]))() 
                    else:
                        records = await sync_to_async(lambda: list(Users.objects.all().order_by('?').defer('name', 'last_activity', 'ref_code')))()
                    count = 0
                    for obj in records:
                        try:
                            await asyncio.sleep(1)  # Задержка для того чтобы удовлетворить условия телеграма 
                            await bot.copy_message(str(obj.external_id), message.chat.id, data['admin_message_id'], reply_markup=data['admin_keyboard_add'])
                            count += 1
                        except:
                            print(f'Пользователя - {str(obj.external_id)} не существует в базе')
                            await obj.adelete()
                    await bot.send_message(message.chat.id, f'Сообщение отправлено: {count} пользователям')                        
            else:       
                await bot.delete_message(message.chat.id, message.id)
                await bot.send_message(message.chat.id, 'Все отменено. ', reply_markup=main_keyboard)
                await bot.delete_state(message.from_user.id, message.chat.id)               


# Добавления сериала и видео к нему с помощью приватного канала ---- ----- ----- ----- -----
        @bot.channel_post_handler(content_types=['video', 'text', 'photo'])
        async def addBDfilm(message):
            chat_info = await bot.get_chat(message.chat.id)
            await sync_to_async(Channel.objects.get_or_create)(
                defaults={'name_channel': chat_info.username},
                id_channel=message.chat.id,) #добавления канала в базу
            id = await sync_to_async(lambda: Channel.objects.get(id_channel=message.chat.id))() # получение строки из канала

            if id.is_super_channel:
                # Функция для добавления видео в бд
                async def add_video(message_text, id_video):
                    if message_text:                        
                        message_text_list = message_text.split(' ; ')
                        if str(message_text_list[2]).isdigit() and len(message_text_list) == 3:
                            try:
                                s = await sync_to_async(lambda: Series.objects.get(id=int(message_text_list[2])))()
                            except:
                                s, _ = await sync_to_async(lambda: Series.objects.get_or_create(name = message_text_list[2]))()
                        elif len(message_text_list) == 3:  # последняя строчка это названия cериала(аниме) в которое добавлять видео можно писать просто id группы видосов
                            s, _ = await sync_to_async(lambda: Series.objects.get_or_create(name = message_text_list[2]))()
                        else:
                            await bot.send_message(message.chat.id, f'📛 <b>Данные под видео недействительны!</b>', parse_mode='HTML')
                            return False # Выходим из функции если что то не верно
                        number = None
                        video_counts = await sync_to_async(lambda: list(Video.objects.values('series_id', 'season').annotate(num_videos=Count('id'))))()                                    
                        for video_count in video_counts: 
                            if await sync_to_async(lambda: Series.objects.get(id=video_count['series_id']).name)() == s.name:
                                if int(video_count['season']) == int(message_text_list[0]):
                                    number = int(video_count['num_videos']) + 1
                        if not number:
                            number = 1
              
                        video = await sync_to_async(lambda: Video.objects.create(
                            series = s,
                            video_id = id_video,
                            season = message_text_list[0], # первая строчка номер сезоня
                            number = number, # номер серии
                            name =  message_text_list[1],  # вторая строчка это название серии
                        ))()
                        await bot.send_message(
                            message.chat.id, 
                            f'Видео успешно добавлено! \r\n{video.name}, к сериалу: <code>{s.name}</code> \r\nCерия №{video.number}, сезон {video.season}\r\n #{s.name}', 
                            parse_mode='HTML'
                            )
                        cache.delete('all_series') # Удаляем кэш

                # Если мы отвечаем на сообщение чтобы сразу все подвязать в базу
                if message.reply_to_message:
                    id_video = message.reply_to_message.video.file_id
                    if message.text == 'repl': # Пишим repl чтобы видео добавилось в базу данных с данными под самим видео, не вписывая новые!
                        message_text = message.reply_to_message.caption
                        await add_video(message_text, id_video)
                    elif len(message.text.split(' ; ')) == 3: # Или сразу пишем все для добавления в базу
                        message_text = message.text
                        await add_video(message_text, id_video)
                    else:
                        await bot.send_message(message.chat.id, f'📛 <b>Данные недействительны!</b>', parse_mode='HTML')

                if message.content_type == "text" and message.text == "/help":
                    await bot.delete_message(message.chat.id, message.id)
                    await bot.send_message(message.chat.id, settings.HELP_CHANNEL, parse_mode='HTML')

                if message.content_type == "video":
                    id_video = message.video.file_id
                    message_text = message.caption    
                    await add_video(message_text, id_video)

                # Постер к сериалу
                if message.content_type == "photo":
                    if settings.CHANGE_DESIGN and (message.caption == "Start message" or message.caption == "sm"):  # Добавление фото после команды /start
                            with open("StartMessageID.txt", "w") as f:
                                f.write(message.photo[0].file_id)
                            await bot.send_message(message.chat.id, f'Успешно добавлено изображение в начальное сообщение')
                    elif settings.CHANGE_DESIGN and (message.caption == "List message" or message.caption == "lm"):  # Добавление фото в список
                            with open("ListMessageID.txt", "w") as f:
                                f.write(message.photo[0].file_id)
                            await bot.send_message(message.chat.id, f'Успешно добавлено изображение для списка')
                    elif len(message.caption.split(' ; ')) == 2:
                        id_photo = message.photo[0].file_id
                        message_text_photo = message.caption
                        message_text_list = message_text_photo.split(' ; ')
                        s, cre = await sync_to_async(lambda: Series.objects.get_or_create(
                            name = message_text_list[0],          #первая строчка названия сериала
                            defaults={
                            'poster':  id_photo,
                            'description': message_text_list[1] # вторая строчка описание этого сериала
                            }))()
                        if not cre:
                            s.poster = str(id_photo)
                            s.description = message_text_list[1]
                            await s.asave()
                            await bot.send_message(
                                message.chat.id, 
                                f'Успешно изменён сериал \r\nимя: <code>{s.name}</code> \r\nОписание: {s.description} \r\n#{s.name}', 
                                parse_mode='HTML'
                                )
                        else:
                            await bot.send_message(
                                message.chat.id, 
                                f'Успешно добавлен сериал \r\nимя: <code>{s.name}</code> \r\nОписание: {s.description}\r\n#{s.name}', 
                                parse_mode='HTML'
                                )
                        cache.delete('all_series') # Удаляем кэш
                    else:
                        await bot.send_message(message.chat.id, f'Фото не было никуда добавлено, перепроверьте введенные данные')

        # Основное меню настраиваться в конфиге
        @bot.message_handler(content_types=['text'])
        async def work(message):
            #try:
            if await update_activity(message.chat.id): # Обновление последней активности
                if await subscription_check(message):    # Проверка на подписку на рекламные каналы
                    for key, value in settings.KEYBOARD_CONFIG.items():
                        if message.text == value['title']:
                            callback = value['callback']
                            await globals()[callback](message)
                            return
            else:
                await bot.send_message(message.chat.id, settings.BAN_NESSAGE, reply_markup=main_keyboard, parse_mode='html')
            #except:
                #await bot.send_message(message.chat.id, f'😨 Произошла ошибка! введите <code>/start</code>', parse_mode='HTML')

        # Регестрация фильтров
        bot.add_custom_filter(asyncio_filters.StateFilter(bot))
        bot.add_custom_filter(asyncio_filters.TextMatchFilter())


        # Запуск на системе вебхуков
        if settings.WEBHOOK_WORK:
            print('''
- - - - - - - - - - - - - - - - - - - - - - - - - 
                  
Please install uvicorn and fastapi in order to use `run_webhooks` method.

Quick'n'dirty SSL certificate generation:

openssl genrsa -out webhook_pkey.pem 2048
openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
                  
- - - - - - - - - - - - - - - - - - - - - - - - -   
                  ''')      
            WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Path to the ssl certificate
            WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Path to the ssl private key
            if settings.DEBUG:
                response = requests.get('https://ifconfig.me')
                if response.status_code == 200:
                    ip_address = response.text.strip()
                    print(f"\nPublic IP: {ip_address}\n")
                else:
                    print("\nError fetching IP address\n")
                DOMAIN = ip_address
            else:     
                DOMAIN = settings.ALLOWED_HOSTS[0] # either domain, or ip address of vps
            # it uses fastapi + uvicorn
            asyncio.run(bot.run_webhooks(
                listen=DOMAIN,
                port=8443,
                certificate=WEBHOOK_SSL_CERT,
                certificate_key=WEBHOOK_SSL_PRIV,
                debug=settings.DEBUG,  
                max_connections=100,          
                ))
        elif settings.DEBUG:
            asyncio.run(bot.delete_webhook(True))
            asyncio.run(bot.polling())
        else:
            asyncio.run(bot.delete_webhook(True))
            asyncio.run(bot.infinity_polling(timeout=50))
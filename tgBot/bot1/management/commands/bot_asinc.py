import asyncio #база для асинхроной работы бота
import logging #дебаг режим
import telebot #база бота нашего
import matplotlib.pyplot as plt #пострение графика активности
import io #для работы с байтами 
import datetime

from django.db.models import Q
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.conf import settings
from asgiref.sync import sync_to_async # способ работы в асинхронном режими Djabgo ORM запросов

from bot1.models import * # импорт всех моделей Django

from fuzzywuzzy import fuzz # модуль для поиска с ошибками
from pathlib import Path # Требуется для корректной работы с файлами
from aiofiles import open as aio_open  # Import for async file operations
from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot, types, ExceptionHandler
from telebot.asyncio_storage import StateMemoryStorage # способ храниения состояний пользователей
from telebot.asyncio_handler_backends import State, StatesGroup # состояния


# включение/выключение дебага в settings.py
if settings.DEBUG:
    logger = telebot.logger
    telebot.logger.setLevel(logging.DEBUG)  # Outputs debug messages to console.
    class MyExceptionHandler(ExceptionHandler):
        async def handle(self, exception):
            logger.error(exception)

    bot = AsyncTeleBot(settings.BOT_TOKEN, state_storage=StateMemoryStorage(), exception_handler=MyExceptionHandler())
else:
    bot = AsyncTeleBot(settings.BOT_TOKEN, state_storage=StateMemoryStorage())

# FSM
class MyStates(StatesGroup):
    search_video = State()
    search_series = State()
       # admin states
    admin_keybord_add_set = State()
    admin_quantity_users = State()
    admin_text_add = State()
    admin_confirmation = State()

# клавиатуры
main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
for key, value in settings.KEYBOARD_CONFIG.items():
    main_keyboard.add(types.KeyboardButton(value['title']))

cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel_keyboard.add(types.KeyboardButton(settings.CANCEL_MESSAGE)) 

keyboard_next_video_list = types.InlineKeyboardMarkup()
button = types.InlineKeyboardButton("Следующая страница ▶️", callback_data='next_list')
keyboard_next_video_list.row(button)

# обновление последней активности
async def update_activity(external_id):
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
                service_usage = ServiceUsage(date=current_date, count=1)
                await service_usage.asave()
            else:
                # Если запись уже существует, увеличиваем счетчик на 1
                service_usage.count += 1
                await service_usage.asave()        
        await user.update_last_activity()
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
    return await sync_to_async(lambda: list(Series.objects.all()))()
async def send_page(message):
    msg = await bot.send_message(message.chat.id, settings.LIST_MESSAGE)
    await send_page1(msg)
# Функция для отправки сообщения с клавиатурой
async def send_page1(message, current_page=1):
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

# поиск сериала
async def search_obj_series(query):
    # Если запрос - это число, ищем по id
    if str(query).isdigit():
        series = await sync_to_async(lambda: list(Series.objects.filter(id=int(query)).all()))()
        if series:
            return series[0]
    else:
        # Иначе, используем fuzzywuzzy для поиска по имени
        series = await sync_to_async(lambda: list(Series.objects.filter(Q(name__icontains=query) | Q(name__iexact=query))))()
    if not series:
        return None  # Объект не найден 
    # фильтруем по нашей схожести равной 70
    filtered_series = [item for item in series if fuzz.ratio(item.name, query) >= 70]
    # Если найден только один объект, возвращаем его
    
    if len(filtered_series) == 1:
        return filtered_series[0]
    # Если найдено несколько объектов, возвращаем объект с наивысшим коэффициентом схожести
    best_match = max(filtered_series, key=lambda x: fuzz.ratio(x.name, query), default=None)
    return best_match   

class Command(BaseCommand):
    help = 'Async Telegram bot.'       

    def handle(self, *args, **kwargs):
        print("\n--- Bot runing ---\n")

        # обработчик инлайн клавиатуры
        @bot.callback_query_handler(func=lambda call: True)
        async def handle_button_click(call):
            await update_activity(call.message.chat.id) # обновление последней активности
            if call.data == 'next_list':
                await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                list1 = call.message.text.split('/')
                list1 = list1[0].split()
                start = list1[len(list1)-1]
                await list_mode(call.message, int(start), int(start)+25)

            if call.data.split('-')[0] == 'start_watching': # Первая серия под сериалом
                obj = await sync_to_async(lambda: Series.objects.get(id=int(call.data.split('-')[1])))()
                await bot.delete_state(call.message.chat.id, call.message.chat.id)
                await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                await search_video(call.message, id_series=obj.id, season=1, number=1)

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
                        try:
                            video = await sync_to_async(lambda: Video.objects.get(id=call.data.split('-')[1]))()
                            if await sync_to_async(lambda: list(Video.objects.filter(series_id=video.series_id, season=video.season, number=video.number+1).all()))():
                                await search_video(call.message, id_series=video.series_id, season=video.season, number=video.number+1)
                            elif await sync_to_async(lambda: list(Video.objects.filter(series_id=video.series_id, season=video.season+1, number=1).all()))():
                                await search_video(call.message, id_series=video.series_id, season=video.season+1, number=1)
                            else:
                                await bot.send_message(call.message.chat.id,'Это было последнее видеo😢', reply_markup=main_keyboard)
                        except:
                            await bot.send_message(call.message.chat.id,'Произошла ошибка🤬', reply_markup=main_keyboard)

            # Закрытие панельки
            if call.data == 'cancel':
                await bot.delete_message(call.message.chat.id, call.message.message_id)
            if call.data.split('-')[0] == 'add':
                if await sync_to_async(lambda: list(Users.objects.filter(external_id=int(call.data.split('-')[1]), is_superuser=True).all()))():
                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                    await bot.send_message(call.message.chat.id, f'Введите клавиатуру так: \r\n<code>Название_кнопки - url </code>:', reply_markup=cancel_keyboard, parse_mode='HTML')
                    await bot.set_state(call.message.chat.id, MyStates.admin_keybord_add_set, call.message.chat.id)

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
                await search_series(call.message, await search_obj_series(call.data.split("_")[1]))

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

            # обнуления рекламной подписки для всех пользователей
            if call.data == 'reset_is_subscription':
                await bot.delete_message(call.message.chat.id, call.message.id)
                users = await sync_to_async(lambda: list(Users.objects.all()))()
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
            if call.data == 'fail_txt_bd':
                await bot.delete_message(call.message.chat.id, call.message.id)
                # Создаем файл с ID пользователей 
                async def write_file(users, filename):
                    async with aio_open(filename, 'w') as file:
                        async for user in users:
                            await file.write(f'{user.external_id}\n')
                # Отправляем его
                async def send_file(bot, chat_id, filename):
                    with open(filename, 'rb') as file:
                        await bot.send_document(chat_id, file, caption=f'Список пользователей ({timezone.now().strftime("%Y-%m-%d %H:%M:%S")})')

                users = await sync_to_async(lambda: Users.objects.all())()
                filename = 'users.txt'
                await write_file(users, filename)
                await send_file(bot, call.message.chat.id, filename)

                
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

        @bot.message_handler(commands=['start'])
        async def start(message):    
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

            user, created = await sync_to_async(Users.objects.get_or_create)(
                external_id=message.from_user.id,
                defaults={'name': message.from_user.username,}
            )
    
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
                            await bot.send_message(message.chat.id, settings.MESSAGE_START, reply_markup=main_keyboard, parse_mode="HTML")
                    else:
                        await bot.send_message(message.chat.id, f"У вас уже имеется реферальный код - <code>{user.ref_code}</code>", parse_mode='HTML')
                else:
                    if text.isdigit and not len(text.split('_')) == 3:
                        await search_series(message, await search_obj_series(int(text)))
                    elif len(text.split('_')) == 3:
                        text_list = text.split('_')
                        await search_video(message, id_series=int(text_list[0]), season=int(text_list[1]), number=int(text_list[2]))
            else:
                if created: 
                    # Создаем либо возращаем на то сколькоп ришло к боту просто от команды /start
                    statistic_code, _ = await sync_to_async(lambda: StatisticRef.objects.get_or_create(name_code='local'))()
                    statistic_code.user_sdded += 1
                    await statistic_code.asave()  
                    # Ставь рефералку того что юзер просто использовал бота без рефки
                    user.ref_code = 'local'
                    await user.asave()  

                    await bot.send_message(message.chat.id, "Обязательно ознакомся с нашим функционалом!", reply_markup=main_keyboard)
                    await bot.send_message(message.chat.id, settings.MESSAGE_START, reply_markup=main_keyboard, parse_mode="HTML")
                else:
                    await bot.send_message(message.chat.id, settings.MESSAGE_START, reply_markup=main_keyboard, parse_mode="HTML") 

        # Поиск конкретного сериала  ---- core состовляющая
        @bot.message_handler(state=MyStates.search_series)
        async def search_series(message, obj=None):          
            if not obj:
                obj = await search_obj_series(message.text)
            
            if obj:
                video_counts = await sync_to_async(lambda: list(Video.objects.values('series_id', 'season').annotate(num_videos=Count('id'))))()
                        
                text_msg_season = ''
                for video_count in video_counts: 
                    if await sync_to_async(lambda: Series.objects.get(id=video_count['series_id']).name)() == obj.name:
                        text_msg_season += f"- сезон {video_count['season']}: серий {video_count['num_videos']}\r\n"

                keyboard_start = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("✨ Смотреть первую серию >", callback_data=f'start_watching-{obj.id}')
                keyboard_start.row(button)
                try:
                    await bot.send_photo(message.chat.id, obj.poster,
                                caption= str(f"⚡️ <b>{obj.name}</b>\r\n<i>{obj.description}</i>\r\n{text_msg_season}"), reply_markup=keyboard_start, parse_mode='HTML')
                except:
                    await bot.send_message(message.chat.id, f"⚡️ <b>{obj.name}</b>\r\n<i>{obj.description}</i>\r\n{text_msg_season}", reply_markup=keyboard_start, parse_mode='HTML')
                
                await bot.send_message(message.chat.id, settings.SEARCH_VIDEO_TEXT ,reply_markup=cancel_keyboard, parse_mode='HTML')
                await bot.set_state(message.chat.id, MyStates.search_video, message.chat.id)
                async with bot.retrieve_data(message.chat.id, message.chat.id) as data:
                    data['id_series'] = obj.id
                    
            else:
                await bot.send_message(message.chat.id, settings.ERROR_VIDEO)  

        # Поиск видо как после сериала так и как отдельный метод для вызова где угодно
        @bot.message_handler(state=MyStates.search_video)
        async def search_video(message, id_series=None, season=None, number=None):
            if not id_series:
                async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:    
                    id_series = data['id_series']
            if not season and not number:
                list_text = message.text.split()
                if len(list_text) == 2:
                    season = list_text[0]
                    number = list_text[1]
                else:
                    await bot.send_message(message.chat.id, settings.ERROR_VIDEO)
                    return
            try:
                obj_video = await sync_to_async(lambda: Video.objects.get(series_id=id_series,season=season ,number=number))()

                keyboard_next_video = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("▶️ Следующая серия", callback_data=f'next_video-{obj_video.id}')
                keyboard_next_video.row(button)
                button_share = types.InlineKeyboardButton("📢 Поделится", 
                    url=f'https://t.me/share/url?url=t.me/{(await bot.get_me()).username}?start={id_series}_{obj_video.season}_{obj_video.number}') #создание ссылки поделится
                keyboard_next_video.row(button_share)

                await bot.send_video(message.chat.id, obj_video.video_id,reply_markup=keyboard_next_video ,
                                caption=f'Сезон {obj_video.season}, cерия №{obj_video.number}, {obj_video.name}')
                await bot.send_message(message.chat.id, settings.ENJOY_WATCHING , reply_markup=main_keyboard)
                await bot.delete_state(message.from_user.id, message.chat.id)
            except:
                await bot.send_message(message.chat.id, settings.ERROR_VIDEO)

        # Альтернативный список по команде /list
        @bot.message_handler(commands=['list'])
        async def list_mode(message, start_index=0, end_index=45): 
            async def objects_Series(start_index, end_index):    
                return await sync_to_async(lambda: list(Series.objects.all()[start_index:end_index]))()
            all_series = await objects_Series(start_index, end_index)

            async def generate_string(series, bot):
                return f'├ ▸<a href="t.me/{(await bot.get_me()).username}?start={series.id}"> {series.name}</a> ◂'
            data_strings = await asyncio.gather(*[generate_string(series, bot) for series in all_series])

            final_string = "\r\n".join(data_strings)

            async def count_Series():
                count = await sync_to_async(Series.objects.count)()
                return count
            count = await count_Series()

            if count > end_index:
                await bot.send_message(message.chat.id, f'{settings.LIST_MESSAGE} {final_string} \r\n│\r\n└Показано  {end_index}/{count}', reply_markup=keyboard_next_video_list, parse_mode='HTML')
            else:
                keyboard_next_video_list_end = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("Это весь наш контен 👾", callback_data='no_work_date')
                keyboard_next_video_list_end.row(button)
                await bot.send_message(message.chat.id, settings.LIST_MESSAGE + final_string, reply_markup=keyboard_next_video_list_end, parse_mode='HTML')


        # Админ команды
        @bot.message_handler(commands=['admin'])
        async def handle_admin_command(message):
            if await sync_to_async(lambda: list(Users.objects.filter(external_id=message.from_user.id, is_superuser=True).all()))():
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                button = types.InlineKeyboardButton("💌Веб панель", url=settings.ADMIN_PANEL_URL)
                button1 = types.InlineKeyboardButton("✏️Написать рекламаный пост", callback_data=f'add-{message.from_user.id}')
                button2 = types.InlineKeyboardButton("🔄Обновить проверку на подписку", callback_data=f'reset_is_subscription')
                button3 = types.InlineKeyboardButton("📊График активности юзеров", callback_data=f'graf')
                button4 = types.InlineKeyboardButton("🗂Выгрузить базу.txt Telegram ID", callback_data=f'fail_txt_bd')
                buttonx = types.InlineKeyboardButton(" -- Закрыть ❌ -- ", callback_data='cancel')
                keyboard.add(button, button1, button2, button3, button4, buttonx)     
                await bot.send_message(message.from_user.id, '💌💌💌--Админ панель--💌💌💌', reply_markup=keyboard)
            else:
                await bot.send_message(message.from_user.id, f'за покупкой рекламы > {settings.CONTACT_TS}', reply_markup=main_keyboard, parse_mode='HTML')
            await bot.delete_message(message.chat.id, message.message_id)
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
                    await bot.send_message(message.chat.id, 'Введите текст(вы можете добавить фото или видео) рекламы(Для использования отдельных шрифтов используйте HTML разметку телеграмма): ')
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
                        records = await sync_to_async(lambda: list(Users.objects.all().order_by('?')[:int(data['admin_quantity_users'])]))() # Oпределенный рэндж рассылки
                    else:
                        records = await sync_to_async(lambda: list(Users.objects.all().order_by('?')))()
                    count = 0
                    for obj in records:
                        try:
                            await asyncio.sleep(1)
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
                if message.content_type == "text" and message.text == "/help":
                    await bot.delete_message(message.chat.id, message.id)
                    await bot.send_message(message.chat.id, settings.HELP_CHANNEL, parse_mode='HTML')

                if message.content_type == "video":
                    id_video = message.video.file_id
                    message_text = message.caption    
                    if message_text:                        
                        message_text_list = message_text.split(' ; ')
                        if str(message_text_list[2]).isdigit():
                            try:
                                s = await sync_to_async(lambda: Series.objects.get(id=int(message_text_list[2])))()
                            except:
                                s, _ = await sync_to_async(lambda: Series.objects.get_or_create(name = message_text_list[2]))()
                        else:                              # последняя строчка это названия cериала(аниме) в которое добавлять видео можно писать просто id группы видосов
                            s, _ = await sync_to_async(lambda: Series.objects.get_or_create(name = message_text_list[2]))()
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
                        await bot.send_message(message.chat.id, f'Видео успешно добавлено! \r\n{video.name}, к сериалу: <code>{s.name}</code> \r\nCерия №{video.number}, сезон {video.season}\r\n #{s.name}', parse_mode='HTML')
                if message.content_type == "photo":
                    id_photo = message.photo[0].file_id
                    message_text_photo = message.caption
                    message_text_list = message_text_photo.split(' ; ')
                    s, cre = await sync_to_async(lambda: Series.objects.get_or_create(
                        name = message_text_list[0],          #первая строчка названия сериала
                        defaults={
                          'poster':  id_photo,
                          'description': message_text_list[1] # вторая строчка описание этого сериала
                        }))()
                    await bot.send_message(message.chat.id, f'Успешно добавлен сериал \r\nимя: <code>{s.name}</code> \r\nОписание: {s.description}\r\n#{s.name}', parse_mode='HTML')
    
                    if not cre:
                        s.poster = id_photo
                        s.description = message_text_list[1]
                        s.asave()
                        await bot.send_message(message.chat.id, f'Успешно изменён сериал \r\nимя: <code>{s.name}</code> \r\nОписание: {s.description} \r\n#{s.name}', parse_mode='HTML')

        # Основное меню настраиваться в конфиге
        @bot.message_handler(content_types=['text'])
        async def work(message):
            try:
                await update_activity(message.chat.id) # Обновление последней активности
                if await subscription_check(message):    # Проверка на подписку на рекламные каналы
                    for key, value in settings.KEYBOARD_CONFIG.items():
                        if message.text == value['title']:
                            callback = value['callback']
                            await globals()[callback](message)
                            return
            except:
                await bot.send_message(message.chat.id, f'😨 Произошла ошибка! введите <code>/start</code>', parse_mode='HTML')

        # Регестрация фильтров
        bot.add_custom_filter(asyncio_filters.StateFilter(bot))
        bot.add_custom_filter(asyncio_filters.TextMatchFilter())


        asyncio.run(bot.polling())#infinity_polling(timeout=50)
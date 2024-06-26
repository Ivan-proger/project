from django.db import models
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async
from datetime import timedelta


# Куда будут привязаны все видео
class Series(models.Model):
    poster = models.CharField(max_length=257, blank=True, default='', verbose_name='Изображение для сериала(по ID телеграмма)')
    name = models.CharField(max_length=40)
    description = models.TextField(blank=True, default='', verbose_name='Описание')
    is_release = models.BooleanField(default=False, verbose_name='Аниме доступно пользователем')

    class Meta:
        verbose_name = 'Сериал'
        verbose_name_plural = 'Сериалы'

    def __str__(self):
        return self.name
    
# Юзеры🥰
class Users(models.Model):
    series = models.ManyToManyField(Series, verbose_name='Просмотренное за месяц')
    external_id = models.PositiveIntegerField(verbose_name='Телеграм ID')
    name = models.CharField(max_length=32, blank=True, null=True, default="")
    is_superuser = models.BooleanField(default=False, verbose_name='Является ли пользователь админом')
    is_subscription = models.BooleanField(default=False, verbose_name='Подписался ли пользователь на каналы-спосноры')
    last_activity = models.DateTimeField(default=timezone.now, verbose_name='Последняя активность')
    ref_code = models.CharField(max_length=20, verbose_name="Код рефералки", blank=True, null=True, default=None)
    messages_per_second = models.IntegerField(verbose_name="Количество вызовов в секунду", default=0)
    ban_time = models.DateTimeField(default=None, blank=True, null=True, verbose_name='Забанен во время: ')
    is_ban = models.BooleanField(default=False, verbose_name='Забанен')

    @sync_to_async
    def update_last_activity(self):
        current_date = timezone.now()
        if self.ban_time is not None:
            if self.ban_time <= (current_date - timedelta(minutes=1)) and self.is_ban:
                self.is_ban = False
        if self.last_activity.second == current_date.second:
            self.messages_per_second += 1
            if self.messages_per_second >= settings.MESSAGES_PER_SECOND:
                self.ban_time = current_date
                self.is_ban = True
        else:
            self.messages_per_second = 1
        # Проверяем, была ли last_activity в прошлом месяце
        if self.last_activity.year == current_date.year:
            if self.last_activity.month == current_date.month - 1 or (self.last_activity.month == 12 and current_date.month == 1):
                self.series.clear()

        self.last_activity = current_date
        self.save()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        if self.name:
            return f'{self.name} ({str(self.external_id)})'
        else:
            return str(self.external_id)
        
#конкретно все видео в боте    
class Video(models.Model):
    series = models.ForeignKey(Series, on_delete = models.CASCADE, verbose_name='Какому сериалу принадлежит')
    season = models.PositiveIntegerField(verbose_name='Номер сезона')
    number = models.PositiveIntegerField(verbose_name='Номер серии')
    video_id = models.CharField(max_length=64, verbose_name='ID видео файла из тг')
    name = models.CharField(max_length=40)

    class Meta:
        verbose_name = 'Видео'
        verbose_name_plural = 'Видео'

    def __str__(self):
        return self.name
    
#все каналы куда добавляется бот    
class Channel(models.Model):
    id_channel = models.TextField(max_length=32)
    is_super_channel = models.BooleanField(default=False, verbose_name='Является ли канал супер важным для постинга сериалов')
    id_advertising = models.BooleanField(default=False, verbose_name='Канал для рекламы')
    name_channel = models.TextField(max_length=64, blank=True, null=True, default="channel")
    subscribers_added = models.PositiveIntegerField(verbose_name="Пришло подписчиков", default=0)

    class Meta:
        verbose_name = 'Каналы'
        verbose_name_plural = 'Каналы'

    def __str__(self):
        if self.name_channel:
            return f'{self.name_channel} ({str(self.id_channel)})'
        else:
            return str(self.id_channel)


# Статистика сервиса
class ServiceUsage(models.Model):
    date = models.DateField(unique=True)
    count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Статистика активности'
        verbose_name_plural = 'Статистика активности'

    def __str__(self):
        return f'Статистика за {self.date}'

# Статистика рефералок
class StatisticRef(models.Model):
    name_code = models.CharField(max_length=20, verbose_name="Код рефералки")
    user_sdded = models.PositiveIntegerField(verbose_name="Пришло юзеров", default=0)

    class Meta:
        verbose_name = 'Статистика рефералок'
        verbose_name_plural = 'Статистика рефералок'

    def __str__(self):
        return f'Статистика по коду `{self.name_code}`'

# Статистика сериалов
class SeriesUsage(models.Model):
    series = models.ForeignKey(Series, on_delete = models.CASCADE, verbose_name='Для: ')
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Статистика сериала'
        verbose_name_plural = 'Статистика сериалов'

    def __str__(self):
        return f'Статистика по `{self.series}` за {str(self.date)[:7]}'
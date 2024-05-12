from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.conf import settings
from .models import Series

# Апдейтер
def update_all_series_cache():
    cache.delete('all_series')
    if settings.DEBUG:
        print('\nReload `all_series` cache! \n')

@receiver(post_save, sender=Series)
def series_changed(sender, instance, created, **kwargs):
    # Обновление кэша после сохранения модели Series
    if instance.is_release: 
        update_all_series_cache()

@receiver(post_delete, sender=Series)
def series_deleted(sender, instance, **kwargs):
    # Обновление кэша после удаления модели Series
    update_all_series_cache()

# Generated by Django 5.0 on 2024-02-21 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0019_remove_channel_advertising_maximum'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='channel',
            options={'verbose_name': 'Каналы', 'verbose_name_plural': 'Каналы'},
        ),
        migrations.AlterModelOptions(
            name='video',
            options={'verbose_name': 'Видео', 'verbose_name_plural': 'Видео'},
        ),
        migrations.AlterField(
            model_name='channel',
            name='id_advertising',
            field=models.BooleanField(default=False, verbose_name='Канал для рекламы'),
        ),
    ]

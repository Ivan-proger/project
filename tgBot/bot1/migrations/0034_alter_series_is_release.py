# Generated by Django 5.0 on 2024-04-15 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0033_series_is_release'),
    ]

    operations = [
        migrations.AlterField(
            model_name='series',
            name='is_release',
            field=models.BooleanField(default=False, verbose_name='Аниме доступно пользователем'),
        ),
    ]

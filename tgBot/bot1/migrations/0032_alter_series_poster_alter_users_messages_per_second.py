# Generated by Django 5.0 on 2024-04-10 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0031_alter_users_options_users_ban_time_users_is_ban_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='series',
            name='poster',
            field=models.CharField(blank=True, default='', max_length=257, verbose_name='Изображение для сериала(по ID телеграмма)'),
        ),
        migrations.AlterField(
            model_name='users',
            name='messages_per_second',
            field=models.IntegerField(default=0, verbose_name='Количество вызовов в секунду'),
        ),
    ]
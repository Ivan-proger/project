# Generated by Django 5.0 on 2024-03-17 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0027_channel_subscribers_added'),
    ]

    operations = [
        migrations.CreateModel(
            name='StatisticRef',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_code', models.CharField(max_length=20, verbose_name='Код рефералки')),
                ('user_sdded', models.IntegerField(default=0, verbose_name='Пришло юзеров')),
            ],
            options={
                'verbose_name': 'Статистика рефералок',
                'verbose_name_plural': 'Статистика рефералок',
            },
        ),
    ]

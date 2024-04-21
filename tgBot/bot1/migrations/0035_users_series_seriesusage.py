# Generated by Django 5.0 on 2024-04-21 19:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0034_alter_series_is_release'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='series',
            field=models.ManyToManyField(to='bot1.series', verbose_name='Просмотренное за месяц'),
        ),
        migrations.CreateModel(
            name='SeriesUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('count', models.IntegerField(default=0)),
                ('series', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot1.series', verbose_name='Для: ')),
            ],
            options={
                'verbose_name': 'Статистика сериала',
                'verbose_name_plural': 'Статистика сериалов',
            },
        ),
    ]

# Generated by Django 5.0 on 2024-04-21 20:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0036_alter_users_series'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seriesusage',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='users',
            name='series',
            field=models.ManyToManyField(to='bot1.series', verbose_name='Просмотренное за месяц'),
        ),
    ]

# Generated by Django 5.0 on 2024-01-06 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0005_series_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='series',
            name='studio',
        ),
        migrations.AddField(
            model_name='series',
            name='poster',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]

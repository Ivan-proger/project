# Generated by Django 5.0 on 2024-01-06 20:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0006_remove_series_studio_series_poster'),
    ]

    operations = [
        migrations.AlterField(
            model_name='series',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
    ]

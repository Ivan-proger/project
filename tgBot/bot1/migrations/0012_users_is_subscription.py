# Generated by Django 5.0 on 2024-02-12 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0011_channel_advertising_maximum_channel_id_advertising'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='is_subscription',
            field=models.BooleanField(default=False),
        ),
    ]

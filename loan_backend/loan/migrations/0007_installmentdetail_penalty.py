# Generated by Django 4.2 on 2023-05-29 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loan', '0006_alter_penalty_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='installmentdetail',
            name='penalty',
            field=models.DecimalField(decimal_places=5, default=0, max_digits=20),
        ),
    ]

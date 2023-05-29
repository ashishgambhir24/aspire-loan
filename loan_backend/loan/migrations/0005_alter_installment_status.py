# Generated by Django 4.2 on 2023-05-29 10:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loan', '0004_penalty'),
    ]

    operations = [
        migrations.AlterField(
            model_name='installment',
            name='status',
            field=models.CharField(choices=[('UNPAID', 'unpaid'), ('PARTIALLY_PAID', 'partially paid'), ('PAID_WITHOUT_PENALTY', 'paid without penalty'), ('PAID', 'paid')], default='UNPAID', max_length=30),
        ),
    ]
# Generated by Django 3.0.5 on 2020-04-13 05:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ranking', '0002_auto_20200410_1730'),
    ]

    operations = [
        migrations.AlterField(
            model_name='twitterdata',
            name='aggregation_period',
            field=models.DateField(verbose_name='集計日'),
        ),
    ]
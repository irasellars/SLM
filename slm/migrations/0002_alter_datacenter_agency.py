# Generated by Django 4.1.7 on 2023-03-26 17:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('slm', '0001_alter_dataavailability_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datacenter',
            name='agency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='data_centers', to='slm.agency'),
        ),
    ]

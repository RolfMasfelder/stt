from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_audio_storage_and_delivery_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="whisper_language",
            field=models.CharField(default="auto", max_length=10),
        ),
    ]

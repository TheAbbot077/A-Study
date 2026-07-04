from django.db import migrations, models
import django.db.models.deletion
import uuid


def generate_sqlite_compatible(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0004_alter_institution_institution_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSetting",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("key", models.CharField(max_length=255)),
                ("value", models.TextField()),
                ("value_type", models.CharField(choices=[("string", "String"), ("integer", "Integer"), ("boolean", "Boolean"), ("json", "JSON")], default="string", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settings", to="users.user")),
            ],
            options={
                "db_table": "settings_user_setting",
                "ordering": ["-updated_at"],
                "unique_together": {("user", "key")},
            },
        ),
        migrations.CreateModel(
            name="InstitutionSetting",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("key", models.CharField(max_length=255)),
                ("value", models.TextField()),
                ("value_type", models.CharField(choices=[("string", "String"), ("integer", "Integer"), ("boolean", "Boolean"), ("json", "JSON")], default="string", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("institution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settings", to="users.institution")),
            ],
            options={
                "db_table": "settings_institution_setting",
                "ordering": ["-updated_at"],
                "unique_together": {("institution", "key")},
            },
        ),
    ]

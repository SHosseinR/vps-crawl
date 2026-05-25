from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def migrate_gpu_fields(apps, schema_editor):
    ServerOffer = apps.get_model("offers", "ServerOffer")
    GpuSpec = apps.get_model("offers", "GpuSpec")

    for offer in ServerOffer.objects.filter(has_gpu=True):
        model = getattr(offer, "gpu_model", None) or offer.name
        memory_mb = getattr(offer, "gpu_memory_mb", None)
        GpuSpec.objects.update_or_create(
            offer=offer,
            defaults={
                "model": model,
                "memory_mb": memory_mb,
                "raw_payload": {
                    "migrated_from_offer_fields": True,
                    "gpu_model": getattr(offer, "gpu_model", None),
                    "gpu_memory_mb": getattr(offer, "gpu_memory_mb", None),
                },
            },
        )


def restore_gpu_fields(apps, schema_editor):
    ServerOffer = apps.get_model("offers", "ServerOffer")
    GpuSpec = apps.get_model("offers", "GpuSpec")

    for spec in GpuSpec.objects.select_related("offer"):
        ServerOffer.objects.filter(pk=spec.offer_id).update(
            gpu_model=spec.model,
            gpu_memory_mb=spec.memory_mb,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("offers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="serveroffer",
            name="region_detail",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.CreateModel(
            name="GpuSpec",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model", models.CharField(max_length=160)),
                ("memory_mb", models.IntegerField(blank=True, null=True)),
                ("raw_payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "offer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gpu",
                        to="offers.serveroffer",
                    ),
                ),
            ],
            options={
                "db_table": "gpu_specs",
                "ordering": ["model"],
            },
        ),
        migrations.AddIndex(
            model_name="gpuspec",
            index=models.Index(fields=["model"], name="gpu_model_idx"),
        ),
        migrations.AddIndex(
            model_name="gpuspec",
            index=models.Index(fields=["memory_mb"], name="gpu_memory_idx"),
        ),
        migrations.RunPython(migrate_gpu_fields, restore_gpu_fields),
        migrations.RemoveField(
            model_name="serveroffer",
            name="gpu_model",
        ),
        migrations.RemoveField(
            model_name="serveroffer",
            name="gpu_memory_mb",
        ),
        migrations.RemoveConstraint(
            model_name="serveroffer",
            name="uq_offer_source_region_period",
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["region_detail"], name="offer_region_detail_idx"),
        ),
        migrations.AddConstraint(
            model_name="serveroffer",
            constraint=models.UniqueConstraint(
                fields=("provider", "source_offer_id", "region", "region_detail", "billing_period"),
                name="uq_offer_source_region_detail_period",
            ),
        ),
    ]

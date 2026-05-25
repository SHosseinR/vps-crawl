from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def attach_gpu_specs_to_offers(apps, schema_editor):
    ServerOffer = apps.get_model("offers", "ServerOffer")
    GpuSpec = apps.get_model("offers", "GpuSpec")

    for spec in GpuSpec.objects.filter(offer__isnull=False):
        ServerOffer.objects.filter(pk=spec.offer_id).update(gpu_id=spec.id)


def restore_gpu_spec_offer(apps, schema_editor):
    GpuSpec = apps.get_model("offers", "GpuSpec")

    for spec in GpuSpec.objects.filter(offers__isnull=False).distinct():
        first_offer = spec.offers.order_by("id").first()
        if first_offer:
            spec.offer_id = first_offer.id
            spec.save(update_fields=["offer"])


class Migration(migrations.Migration):
    dependencies = [
        ("offers", "0002_region_detail_gpu_spec"),
    ]

    operations = [
        migrations.AddField(
            model_name="serveroffer",
            name="gpu",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offers",
                to="offers.gpuspec",
            ),
        ),
        migrations.RunPython(attach_gpu_specs_to_offers, restore_gpu_spec_offer),
        migrations.RemoveField(
            model_name="gpuspec",
            name="offer",
        ),
    ]

from __future__ import annotations

from decimal import Decimal

from django.db import migrations, models


def price_amount_toman(price_amount_irr):
    if price_amount_irr is None:
        return None
    return int(Decimal(price_amount_irr) / Decimal("10"))


def equivalent_hourly_price_toman(price_amount_irr, billing_period):
    toman = price_amount_toman(price_amount_irr)
    if toman is None:
        return None

    period_hours = {
        "hour": Decimal("1"),
        "hourly": Decimal("1"),
        "day": Decimal("24"),
        "daily": Decimal("24"),
        "week": Decimal("168"),
        "weekly": Decimal("168"),
        "month": Decimal("720"),
        "monthly": Decimal("720"),
        "year": Decimal("8760"),
        "yearly": Decimal("8760"),
        "annual": Decimal("8760"),
        "annually": Decimal("8760"),
    }
    hours = period_hours.get((billing_period or "").lower(), Decimal("720"))
    return (Decimal(toman) / hours).quantize(Decimal("0.01"))


def populate_toman_prices(apps, schema_editor):
    ServerOffer = apps.get_model("offers", "ServerOffer")
    for offer in ServerOffer.objects.all().only("id", "price_amount_irr", "billing_period"):
        offer.price_amount_toman = price_amount_toman(offer.price_amount_irr)
        offer.equivalent_hourly_price_toman = equivalent_hourly_price_toman(
            offer.price_amount_irr,
            offer.billing_period,
        )
        offer.save(update_fields=["price_amount_toman", "equivalent_hourly_price_toman"])


class Migration(migrations.Migration):
    dependencies = [
        ("offers", "0003_offer_gpu_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="serveroffer",
            name="price_amount_toman",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="serveroffer",
            name="equivalent_hourly_price_toman",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.RunPython(populate_toman_prices, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["price_amount_toman"], name="offer_price_toman_idx"),
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["equivalent_hourly_price_toman"], name="offer_hourly_toman_idx"),
        ),
        migrations.AlterModelOptions(
            name="serveroffer",
            options={"ordering": ["equivalent_hourly_price_toman", "provider__slug", "name"]},
        ),
    ]

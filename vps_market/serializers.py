from __future__ import annotations

from rest_framework import serializers

from vps_market.models import Provider, ServerOffer


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "slug", "name", "base_url", "created_at", "updated_at"]


class ServerOfferSerializer(serializers.ModelSerializer):
    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = ServerOffer
        fields = [
            "id",
            "provider",
            "source_offer_id",
            "name",
            "region",
            "country",
            "city",
            "category",
            "billing_period",
            "price_amount_irr",
            "original_price_amount",
            "original_price_currency",
            "cpu_cores",
            "ram_mb",
            "disk_gb",
            "disk_type",
            "traffic_gb",
            "bandwidth_mbps",
            "has_gpu",
            "gpu_model",
            "gpu_memory_mb",
            "available",
            "buy_url",
            "source_url",
            "first_seen_at",
            "last_seen_at",
            "updated_at",
        ]

from __future__ import annotations

from rest_framework import serializers

from offers.models import GpuSpec, Provider, ServerOffer


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "slug", "name", "base_url", "created_at", "updated_at"]


class GpuSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = GpuSpec
        fields = ["id", "model", "memory_mb"]


class ServerOfferSerializer(serializers.ModelSerializer):
    provider = ProviderSerializer(read_only=True)
    gpu = GpuSpecSerializer(read_only=True)

    class Meta:
        model = ServerOffer
        fields = [
            "id",
            "provider",
            "source_offer_id",
            "name",
            "region",
            "region_detail",
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
            "gpu",
            "available",
            "buy_url",
            "source_url",
            "first_seen_at",
            "last_seen_at",
            "updated_at",
        ]

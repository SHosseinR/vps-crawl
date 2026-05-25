from __future__ import annotations

from django.db.models import Q, QuerySet
from rest_framework.generics import ListAPIView, RetrieveAPIView

from vps_market.models import Provider, ServerOffer
from vps_market.serializers import ProviderSerializer, ServerOfferSerializer


class ProviderListAPIView(ListAPIView):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    pagination_class = None


class ServerOfferListAPIView(ListAPIView):
    serializer_class = ServerOfferSerializer

    def get_queryset(self) -> QuerySet[ServerOffer]:
        queryset = ServerOffer.objects.select_related("provider").all()
        params = self.request.query_params

        exact_filters = {
            "provider__slug": params.get("provider"),
            "region": params.get("region"),
            "country": params.get("country"),
            "city": params.get("city"),
            "billing_period": params.get("billing_period"),
            "disk_type": params.get("disk_type"),
        }
        for field, value in exact_filters.items():
            if value:
                queryset = queryset.filter(**{field: value})

        queryset = _bool_filter(queryset, "has_gpu", params.get("has_gpu"))
        queryset = _bool_filter(queryset, "available", params.get("available"))
        queryset = _number_filter(queryset, "price_amount_irr", params.get("min_price_irr"), "gte")
        queryset = _number_filter(queryset, "price_amount_irr", params.get("max_price_irr"), "lte")
        queryset = _number_filter(queryset, "cpu_cores", params.get("min_cpu_cores"), "gte")
        queryset = _number_filter(queryset, "ram_mb", params.get("min_ram_mb"), "gte")
        queryset = _number_filter(queryset, "disk_gb", params.get("min_disk_gb"), "gte")
        queryset = _number_filter(queryset, "traffic_gb", params.get("min_traffic_gb"), "gte")

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(category__icontains=search)
                | Q(gpu_model__icontains=search)
                | Q(region__icontains=search)
            )

        return queryset.order_by(*_ordering(params.get("ordering")))


class ServerOfferDetailAPIView(RetrieveAPIView):
    queryset = ServerOffer.objects.select_related("provider").all()
    serializer_class = ServerOfferSerializer


def _bool_filter(queryset: QuerySet[ServerOffer], field: str, value: str | None) -> QuerySet[ServerOffer]:
    if value is None:
        return queryset
    normalized = value.lower()
    if normalized in {"1", "true", "yes"}:
        return queryset.filter(**{field: True})
    if normalized in {"0", "false", "no"}:
        return queryset.filter(**{field: False})
    return queryset


def _number_filter(
    queryset: QuerySet[ServerOffer],
    field: str,
    value: str | None,
    lookup: str,
) -> QuerySet[ServerOffer]:
    if value in {None, ""}:
        return queryset
    try:
        number = float(value)
    except ValueError:
        return queryset
    return queryset.filter(**{f"{field}__{lookup}": number})


def _ordering(value: str | None) -> list[str]:
    allowed = {
        "price_amount_irr",
        "cpu_cores",
        "ram_mb",
        "disk_gb",
        "traffic_gb",
        "bandwidth_mbps",
        "last_seen_at",
        "updated_at",
        "name",
    }
    if not value:
        return ["price_amount_irr", "provider__slug", "name"]

    fields = []
    for raw_field in value.split(","):
        field = raw_field.strip()
        base = field[1:] if field.startswith("-") else field
        if base in allowed:
            fields.append(field)
    return fields or ["price_amount_irr", "provider__slug", "name"]

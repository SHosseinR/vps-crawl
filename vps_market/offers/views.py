from __future__ import annotations

from django.db.models import Count, Max, Min, Q, QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from offers.models import GpuSpec, Provider, ServerOffer
from offers.serializers import ProviderSerializer, ServerOfferSerializer


class ProviderListAPIView(ListAPIView):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    pagination_class = None


@extend_schema(
    parameters=[
        OpenApiParameter("provider", str, description="Provider slug, e.g. iranserver"),
        OpenApiParameter("region", str),
        OpenApiParameter("region_detail", str),
        OpenApiParameter("country", str),
        OpenApiParameter("city", str),
        OpenApiParameter("billing_period", str),
        OpenApiParameter("disk_type", str),
        OpenApiParameter("has_gpu", bool),
        OpenApiParameter("gpu_model", str),
        OpenApiParameter("available", bool),
        OpenApiParameter("min_price_irr", int),
        OpenApiParameter("max_price_irr", int),
        OpenApiParameter("min_price_toman", int),
        OpenApiParameter("max_price_toman", int),
        OpenApiParameter("min_cpu_cores", float),
        OpenApiParameter("min_ram_mb", int),
        OpenApiParameter("min_disk_gb", float),
        OpenApiParameter("min_traffic_gb", float),
        OpenApiParameter("min_gpu_memory_mb", int),
        OpenApiParameter("search", str),
        OpenApiParameter("ordering", str, description="Comma-separated fields, e.g. equivalent_hourly_price_toman,-cpu_cores"),
    ]
)
class ServerOfferListAPIView(ListAPIView):
    serializer_class = ServerOfferSerializer

    def get_queryset(self) -> QuerySet[ServerOffer]:
        queryset = ServerOffer.objects.select_related("provider", "gpu").all()
        params = self.request.query_params

        exact_filters = {
            "provider__slug": params.get("provider"),
            "region": params.get("region"),
            "region_detail": params.get("region_detail"),
            "country": params.get("country"),
            "city": params.get("city"),
            "billing_period": params.get("billing_period"),
            "disk_type": params.get("disk_type"),
        }
        for field, value in exact_filters.items():
            if value:
                queryset = queryset.filter(**{field: value})

        queryset = _bool_filter(queryset, "has_gpu", params.get("has_gpu"))
        gpu_model = params.get("gpu_model")
        if gpu_model:
            queryset = queryset.filter(gpu__model__icontains=gpu_model)
        queryset = _bool_filter(queryset, "available", params.get("available"))
        queryset = _number_filter(queryset, "price_amount_irr", params.get("min_price_irr"), "gte")
        queryset = _number_filter(queryset, "price_amount_irr", params.get("max_price_irr"), "lte")
        queryset = _number_filter(queryset, "price_amount_toman", params.get("min_price_toman"), "gte")
        queryset = _number_filter(queryset, "price_amount_toman", params.get("max_price_toman"), "lte")
        queryset = _number_filter(queryset, "cpu_cores", params.get("min_cpu_cores"), "gte")
        queryset = _number_filter(queryset, "ram_mb", params.get("min_ram_mb"), "gte")
        queryset = _number_filter(queryset, "disk_gb", params.get("min_disk_gb"), "gte")
        queryset = _number_filter(queryset, "traffic_gb", params.get("min_traffic_gb"), "gte")
        queryset = _number_filter(queryset, "gpu__memory_mb", params.get("min_gpu_memory_mb"), "gte")

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(category__icontains=search)
                | Q(gpu__model__icontains=search)
                | Q(region__icontains=search)
                | Q(region_detail__icontains=search)
            )

        return queryset.order_by(*_ordering(params.get("ordering")))


class ServerOfferDetailAPIView(RetrieveAPIView):
    queryset = ServerOffer.objects.select_related("provider", "gpu").all()
    serializer_class = ServerOfferSerializer


@extend_schema(
    responses=inline_serializer(
        name="OfferStatistics",
        fields={
            "providers_count": serializers.IntegerField(),
            "offers_count": serializers.IntegerField(),
            "available_offers_count": serializers.IntegerField(),
            "gpu_offers_count": serializers.IntegerField(),
            "min_price_irr": serializers.IntegerField(allow_null=True),
            "max_price_irr": serializers.IntegerField(allow_null=True),
            "min_price_toman": serializers.IntegerField(allow_null=True),
            "max_price_toman": serializers.IntegerField(allow_null=True),
            "regions": serializers.ListField(child=serializers.DictField()),
            "region_details": serializers.ListField(child=serializers.DictField()),
            "providers": serializers.ListField(child=serializers.DictField()),
            "gpu_models": serializers.ListField(child=serializers.DictField()),
        },
    )
)
class OfferStatisticsAPIView(APIView):
    def get(self, request):
        offers = ServerOffer.objects.all()
        aggregate = offers.aggregate(
            offers_count=Count("id"),
            available_offers_count=Count("id", filter=Q(available=True)),
            gpu_offers_count=Count("id", filter=Q(has_gpu=True)),
            min_price_irr=Min("price_amount_irr"),
            max_price_irr=Max("price_amount_irr"),
            min_price_toman=Min("price_amount_toman"),
            max_price_toman=Max("price_amount_toman"),
        )
        aggregate["providers_count"] = Provider.objects.count()
        aggregate["regions"] = list(
            offers.exclude(region__isnull=True)
            .values("region")
            .annotate(count=Count("id"))
            .order_by("-count", "region")
        )
        aggregate["region_details"] = list(
            offers.exclude(region_detail="")
            .values("region", "region_detail")
            .annotate(count=Count("id"))
            .order_by("region", "region_detail")
        )
        aggregate["providers"] = list(
            offers.values("provider__slug", "provider__name")
            .annotate(count=Count("id"), available_count=Count("id", filter=Q(available=True)))
            .order_by("provider__slug")
        )
        aggregate["gpu_models"] = list(
            offers.filter(gpu__isnull=False)
            .values("gpu__model", "gpu__memory_mb")
            .annotate(count=Count("id"))
            .order_by("gpu__model", "gpu__memory_mb")
        )
        return Response(aggregate)


@extend_schema(
    responses=inline_serializer(
        name="FilterOptions",
        fields={
            "providers": serializers.ListField(child=serializers.DictField()),
            "regions": serializers.ListField(child=serializers.CharField()),
            "region_details": serializers.ListField(child=serializers.DictField()),
            "billing_periods": serializers.ListField(child=serializers.CharField()),
            "disk_types": serializers.ListField(child=serializers.CharField()),
            "gpu_specs": serializers.ListField(child=serializers.DictField()),
        },
    )
)
class FilterOptionsAPIView(APIView):
    def get(self, request):
        offers = ServerOffer.objects.select_related("provider", "gpu")
        return Response(
            {
                "providers": list(Provider.objects.values("slug", "name").order_by("slug")),
                "regions": list(
                    offers.exclude(region__isnull=True)
                    .values_list("region", flat=True)
                    .distinct()
                    .order_by("region")
                ),
                "region_details": list(
                    offers.exclude(region_detail="")
                    .values("region", "region_detail")
                    .distinct()
                    .order_by("region", "region_detail")
                ),
                "billing_periods": list(
                    offers.values_list("billing_period", flat=True).distinct().order_by("billing_period")
                ),
                "disk_types": list(
                    offers.exclude(disk_type__isnull=True)
                    .values_list("disk_type", flat=True)
                    .distinct()
                    .order_by("disk_type")
                ),
                "gpu_specs": list(GpuSpec.objects.values("id", "model", "memory_mb").order_by("model", "memory_mb")),
            }
        )


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
        "price_amount_toman",
        "equivalent_hourly_price_toman",
        "cpu_cores",
        "ram_mb",
        "disk_gb",
        "traffic_gb",
        "bandwidth_mbps",
        "gpu_memory_mb",
        "last_seen_at",
        "updated_at",
        "name",
        "provider",
    }
    if not value:
        return ["equivalent_hourly_price_toman", "provider__slug", "name"]

    fields = []
    for raw_field in value.split(","):
        field = raw_field.strip()
        base = field[1:] if field.startswith("-") else field
        if base in allowed:
            prefix = "-" if field.startswith("-") else ""
            if base == "gpu_memory_mb":
                fields.append(f"{prefix}gpu__memory_mb")
            elif base == "provider":
                fields.append(f"{prefix}provider__slug")
            else:
                fields.append(field)
    return fields or ["equivalent_hourly_price_toman", "provider__slug", "name"]

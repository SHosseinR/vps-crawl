from __future__ import annotations

from django.urls import path

from offers.views import (
    FilterOptionsAPIView,
    OfferStatisticsAPIView,
    ProviderListAPIView,
    ServerOfferDetailAPIView,
    ServerOfferListAPIView,
)


urlpatterns = [
    path("providers/", ProviderListAPIView.as_view(), name="provider-list"),
    path("offers/", ServerOfferListAPIView.as_view(), name="offer-list"),
    path("offers/<int:pk>/", ServerOfferDetailAPIView.as_view(), name="offer-detail"),
    path("statistics/", OfferStatisticsAPIView.as_view(), name="offer-statistics"),
    path("filter-options/", FilterOptionsAPIView.as_view(), name="filter-options"),
]

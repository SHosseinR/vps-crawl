from __future__ import annotations

from django.urls import path

from vps_market.views import ProviderListAPIView, ServerOfferDetailAPIView, ServerOfferListAPIView


urlpatterns = [
    path("providers/", ProviderListAPIView.as_view(), name="provider-list"),
    path("offers/", ServerOfferListAPIView.as_view(), name="offer-list"),
    path("offers/<int:pk>/", ServerOfferDetailAPIView.as_view(), name="offer-detail"),
]

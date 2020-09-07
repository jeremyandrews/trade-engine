from django.urls import path

from . import views


app_name = "trade"

urlpatterns = [
    path('trade/history/', views.TradeHistoryView.as_view(), name='trade-history'),
]

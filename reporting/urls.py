from django.urls import path, register_converter

from . import views, converters


app_name = "reporting"

register_converter(converters.CryptoPair, 'cryptopair')

urlpatterns = [
    path('reporting/block/', views.ReportingBlockView.as_view(), name='reporting-block'),

    path('public/markets/', views.ReportingMarketsView.as_view(), name="public-markets"),
    path('public/<cryptopair:pair>/orderbook/', views.ReportingOrderbookView.as_view(), name="public-orderbook"),
    path('public/<cryptopair:pair>/trades/', views.ReportingTradesView.as_view(), name="public-trades"),
    path('public/<cryptopair:pair>/ticker/', views.ReportingTickerView.as_view(), name="public-ticker"),
]

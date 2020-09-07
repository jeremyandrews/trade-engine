from django.urls import path

from . import views


app_name = "order"

urlpatterns = [
    path('order/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('order/cancel/', views.OrderCancelView.as_view(), name='order-cancel'),
    path('order/history/', views.OrderHistoryView.as_view(), name='order-history'),
]

from django.urls import path

from . import views


app_name = "wallet"

urlpatterns = [
    path('wallet/create-seed/', views.WalletCreateSeedView.as_view(), name='wallet-create-seed'),
    path('wallet/create/', views.WalletCreateView.as_view(), name='wallet-create'),
    path('wallet/list/', views.WalletListView.as_view(), name='wallet-list'),
    path('wallet/transactions/', views.WalletTransactionsView.as_view(), name='wallet-transactions'),
    path('wallet/send/', views.WalletSendView.as_view(), name='wallet-send'),
]

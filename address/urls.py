from django.urls import path

from . import views


app_name = "address"

urlpatterns = [
    path('address/create/', views.AddressCreateView.as_view(), name='address-create'),
    #path('address/list/', views.AddressListView.as_view(), name='address-list'),
]

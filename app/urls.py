from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('api/', include('spauser.urls', namespace='spauser')),
    path('api/', include('spaprofile.urls', namespace='spaprofile')),
    path('api/', include('otp.urls', namespace='otp')),

    path('api/', include('wallet.urls', namespace='wallet')),
    path('api/', include('address.urls', namespace='address')),

    path('api/', include('order.urls', namespace='order')),
    path('api/', include('trade.urls', namespace='trade')),

    path('api/', include('reporting.urls', namespace='reporting')),

    path('admin/', admin.site.urls),
]

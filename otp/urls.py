from django.urls import path, register_converter
from . import views, converters


app_name = 'otp'

register_converter(converters.SixDigitTOTP, 'nnnnnn')
register_converter(converters.SevenEightCharStatic, 'alphanum')

urlpatterns = [
    path('totp/enabled/', views.TOTPEnabledView.as_view(), name='totp-enabled'),
    path('totp/create/', views.TOTPCreateView.as_view(), name='totp-create'),
    path('totp/login/<nnnnnn:token>/', views.TOTPVerifyView.as_view(), name='totp-login'),
    path('totp/delete/', views.TOTPDeleteView.as_view(), name='totp-delete'),
    path('static/create/', views.StaticCreateView.as_view(), name='static-create'),
    path('static/login/<alphanum:token>/', views.StaticVerifyView.as_view(), name='static-login'),
]

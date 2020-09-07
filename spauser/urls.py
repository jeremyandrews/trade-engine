from django.urls import path
from djoser import views as djoser_views
from rest_framework_jwt import views as jwt_views

from . import views


app_name = "spauser"

urlpatterns = [
    # Custom views.
    path('email/available/', views.SpaUserEmailView.as_view(), name='email-available'),
    path('user/view/', views.SpaUserView.as_view(), name='user-view'),
    path('user/delete/', views.SpaUserDeleteView.as_view(), name='user-delete'),
    path('user/edit/email/', views.SpaUserSetUsernameView.as_view(), name='user-edit-email'),
    path('user/edit/password/', views.SpaUserSetPasswordView.as_view(), name='user-edit-password'),
    path('user/login/refresh/', views.SpaUserRefreshJSONWebToken.as_view(), name='user-login-refresh'),
    path('user/logout/all/', views.SpaUserLogoutAllView.as_view(), name='user-logout-all'),

    # Views are defined in Djoser, but we're assigning custom paths.
    path('user/create/', djoser_views.UserCreateView.as_view(), name='user-create'),
    path('user/activate/', djoser_views.ActivationView.as_view(), name='user-activate'),
    path('user/password/reset/', djoser_views.PasswordResetView.as_view(), name='user-password-reset'),
    path('user/password/reset/confirm/', djoser_views.PasswordResetConfirmView.as_view(), name='user-password-reset-confirm'),

    # Views are defined in Rest Framework JWT, but we're assigning custom paths.
    path('user/login/', jwt_views.ObtainJSONWebToken.as_view(), name='user-login'),
]

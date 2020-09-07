from django.urls import path

from . import views


app_name = "spaprofile"

urlpatterns = [
    path('profile/view/', views.SpaProfileView.as_view(), name='profile-view'),
    path('profile/edit/', views.SpaProfileEditView.as_view(), name='profile-edit'),

    path('countries/', views.SpaProfileCountriesView.as_view(), name='countries')
]

from django.urls import path

from . import views

"""Route upload URLs to upload views here."""


urlpatterns = [
    path('', views.FileFieldView.as_view(), name='upload'),
]

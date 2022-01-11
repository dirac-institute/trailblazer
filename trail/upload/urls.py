from django.urls import path

from . import views

"""Route upload URLs to upload views here."""


urlpatterns = [
    path('', views.upload_view, name='upload'),
]

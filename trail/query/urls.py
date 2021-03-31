from django.urls import path

from . import views

"""Route query URLs to query views here."""


urlpatterns = [
    path('', views.index, name='index'),
]

from django.urls import path
from django.views.generic import TemplateView

from . import views

"""Route query URLs to query views here."""


urlpatterns = [
    path('', TemplateView.as_view(template_name='query.html')),
]

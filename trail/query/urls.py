from django.urls import path
from django.views.generic import TemplateView


"""Route query URLs to query views here."""


urlpatterns = [
    path('', TemplateView.as_view(template_name='query.html')),
]

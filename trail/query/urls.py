from query.views import print_results
from django.urls import path
from django.views.generic import TemplateView


"""Route query URLs to query views here."""


#urlpatterns = [
    #path('', TemplateView.as_view(template_name='query.html')),
#]

urlpatterns = [
   path('', print_results, name='gallery'),
]
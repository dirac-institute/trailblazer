from query.views import print_results, index
from django.urls import path


"""Route query URLs to query views here."""


urlpatterns = [
   path('', index, name='query'),
   path('results', print_results, name='results'),
]

from query.views import print_results, index
from django.urls import path
from query.views import ObservationListView
# from django.views.generic import TemplateView


"""Route query URLs to query views here."""


urlpatterns = [
   path('', index, name='query'),
   path('results', print_results, name='results'),
   path("observation", ObservationListView.as_view())
]

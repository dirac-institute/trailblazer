from query.views import print_results, index, MetaDataQuery
from django.urls import path


"""Route query URLs to query views here."""


urlpatterns = [
   path('', index, name='query'),
   path('results', print_results, name='results'),
   path('getMetadata', MetaDataQuery.as_view())
]

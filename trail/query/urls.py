from query.views import print_results, index, MetadataQuery
from django.urls import path


"""Route query URLs to query views here."""


urlpatterns = [
   path('', index, name='query'),
   path('results', print_results, name='results'),
   path('getMetadata', MetadataQuery.as_view()),
   path('getMetadataByWcs', MetadataQuery.as_view()),
]

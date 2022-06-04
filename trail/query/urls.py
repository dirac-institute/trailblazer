from query.views import print_results, index, MetadataQuery, WcsQuery, download_query, ObservatonView
from django.urls import path
from django.contrib import admin


"""Route query URLs to query views here."""


urlpatterns = [
   path('', index, name='query'),
   path('results', print_results, name='results'),
   path('getMetadata', MetadataQuery.as_view()),
   path('download', download_query, name='download_query'),
   path('getMetadataByWcs', WcsQuery.as_view()),
   path("admin", admin.site.urls),
   path("observation", ObservatonView.as_view())
]

from query.views import print_results, index
from query.rest_views import MetadataView, WcsView
from django.urls import path
from django.contrib import admin


"""Route query URLs to query views here."""


urlpatterns = [
    path('', index, name='query'),
    path('results', print_results, name='results'),
#     path('download', download_query, name='download_query'),
    path('metadata', MetadataView.as_view(), name="metadata"),
    path('wcs', WcsView.as_view(), name="wcs"),
]

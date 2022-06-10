from query.views import print_results, index
from query.rest_views import MetadataView
from django.urls import path


"""Route query URLs to query views here."""


urlpatterns = [
    path('', index, name='query'),
    path('results', print_results, name='results'),
    path('metadata', MetadataView.as_view(), name="metadata"),
]

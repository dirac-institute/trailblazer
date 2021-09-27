from query.views import print_results, index, MetadataViewSet, get_metadata
from django.urls import path, include

from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns

"""Route query URLs to query views here."""


router = routers.DefaultRouter()
router.register(r'metadata', MetadataViewSet)


urlpatterns = [
    path('', index, name='query'),
    path('results', print_results, name='results'),
    path('rest/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]


rest2_patterns = format_suffix_patterns([
    path('rest2/metadata/INSTR=<str:instrument>&TEL=<str:telescope>&FIL=<str:filter_name>', get_metadata),
])

urlpatterns.extend(rest2_patterns)




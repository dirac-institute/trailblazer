import django
from django.core.exceptions import FieldError

from rest_framework import mixins, status
from rest_framework import exceptions as rf_error
from rest_framework.views import APIView
from rest_framework.response import Response

from upload.models import Metadata, Wcs
from query.serializers import MetadataSerializer, WcsSerializer

from drf_yasg.utils import swagger_auto_schema



class GenericTableView(mixins.ListModelMixin, APIView):
    queryset = None
    serializer_class = None

    def extract_common_query_keys(self, queryDict, *args, **kwargs):
        # we need a copy to be mutable, see link below
        mutableQD = queryDict.copy()

        # parse out any serializer keys we need.
        serializerKeys = {}
        serializerKeys["fields"] = mutableQD.pop("fields", None)

        # parse out any get_queryset keywords we want
        querysetKeys = {}
        querysetKeys["getWcs"] = mutableQD.pop("getWcs", False)

        # in case something about a get_queryset requires modifying serializer
        # in some way add that logic here
        if querysetKeys["getWcs"]:
            serializerKeys["keepWcs"] = mutableQD.pop("fields", None)
        

        return mutableQD, serializerKeys, querysetKeys


    def get(self, request, *args, **kwargs):
        # See https://docs.djangoproject.com/en/4.0/ref/request-response/#id1
        # Remove keys that do not belong to the query, but are still used, f.e.
        # 'fields' or 'casesensitive'. Make a mutable copy first, then pop
        # always returns a list. Note the pop method supports default key, but
        # isn't documented.
        queryDict, serializerKeys, querysetKeys = self.extract_common_query_keys(request.query_params)

        # unfortunately unpacking operators do not work on QueryDicts like
        # they do on dicts. Items will also return only the last element of
        # a key, if the key is a list. See link above. This is ok here because
        # we do not support OR queries on same fields yet. Additionally we can
        # modify keys here with additional query-related params, f.e.
        # add __icontains, if we want to.
        qparams = {key: value for key, value in queryDict.items()}
        querySet = self.get_queryset(**querysetKeys)
        try:
            if qparams:
                querySet = querySet.filter(**qparams)
            else:
                querySet = querySet.all()
        except FieldError as e:
            # first param should be an error page, but we don't have one yet
            # TODO: I guess see https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpResponseBadRequest
            # on how to make one. The parameter is the redirect link.
            response = django.http.HttpResponseBadRequest("/query")
            response.data = e.args
            return response

        if querysetKeys:
            breakpoint()
        serializer = self.serializer_class(querySet, many=True, **serializerKeys)
        return Response(serializer.data, status=status.HTTP_200_OK)



class MetadataView(GenericTableView):
    queryset = Metadata.objects.all()
    serializer_class = MetadataSerializer

    def get_queryset(self, getWcs=False, *args, **kwargs):
        if getWcs:
            return self.queryset.prefetch_related("wcs_set")
        return self.queryset


class WcsView(GenericTableView):
    queryset = Wcs.objects.all()
    serializer_class = WcsSerializer

    def get_queryset(self, *args, **kwargs):
        # see http://www.tomchristie.com/rest-framework-2-docs/api-guide/filtering
        return self.queryset


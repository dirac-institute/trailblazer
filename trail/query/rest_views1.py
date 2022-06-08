import django
from django.core.exceptions import FieldError

from rest_framework import mixins, status
from rest_framework import exceptions as rf_error
from rest_framework.views import APIView
from rest_framework.response import Response

from upload.models import Metadata, Wcs
from query.serializers import MetadataSerializer

from drf_yasg.utils import swagger_auto_schema



class MetadataView(mixins.ListModelMixin, APIView):
    queryset = Metadata.objects.all()
    serializer_class = MetadataSerializer

    def get(self, request, *args, **kwargs):
        # See https://docs.djangoproject.com/en/4.0/ref/request-response/#id1
        # Remove keys that do not belong to the query, but are still used, f.e.
        # 'fields' or 'casesensitive'. Make a mutable copy first, then pop
        # always returns a list. Note the pop method supports default key, but
        # isn't documented.
        mutableQD = request.query_params.copy()
        fields = mutableQD.pop("fields", None)

        # unfortunately unpacking operators do not work on QueryDicts like
        # they do on dicts. Items will also return only the last element of
        # a key, if the key is a list. See link above. This is ok here because
        # we do not support OR queries on same fields yet. 
        qparams = {key: value for key, value in mutableQD.items()}
        querySet = self.queryset
        try:
            if qparams:
                querySet = querySet.filter(**qparams)
            else:
                querySet = querySet.all()
        except FieldError as e:
            # first param should be an error page, but we don't have one yet
            # TODO: I guess see https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpResponseBadRequest
            # on how to make one.
            response = django.http.HttpResponseBadRequest("/query")
            response.data = e.args
            return response

        serializer = MetadataSerializer(querySet, many=True, fields=fields)
        return Response(serializer.data, status=status.HTTP_200_OK)

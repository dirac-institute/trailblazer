import django
from django.core.exceptions import FieldError

import numpy as np

from rest_framework import mixins, status
from rest_framework import exceptions as rf_error
from rest_framework.views import APIView
from rest_framework.response import Response

from upload.models import Metadata, Wcs
from query.serializers import MetadataSerializer, WcsSerializer

from drf_yasg.utils import swagger_auto_schema


def getXYZFromWcs(ra, dec):
    """Convert ra and dec into xyz coordinates
    """
    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    return {"x": x, "y": y, "z": z}


class GenericTableView(mixins.ListModelMixin, APIView):
    queryset = None
    serializer_class = None

    def get_shared_non_query_keys(self, queryDict, *args, **kwargs):
        # parse out any serializer keys we need.
        serializerParams = {}
        serializerParams["fields"] = queryDict.pop("fields", None)

        # parse out any get_queryset keywords we want, f.e. casesensitive
        querysetParams = {}

        return queryDict, serializerParams, querysetParams

    def get_non_query_keys(self, queryDict, *args, **kwargs):
        # no-op, could be NotImplemented too, makes sense to assume no special
        # keys are allowed for a generic table view though
        return queryDict, {}, {}

    def extract_params(self, queryDict):
        # See https://docs.djangoproject.com/en/4.0/ref/request-response/#id1
        # Remove keys that do not belong to the query, but are still used, f.e.
        # 'fields' or 'casesensitive'. Make a mutable copy first, then pop
        # always returns a list. Note the pop method supports default key, but
        # isn't documented. We need a copy to be mutable, see link.
        mutableQD = queryDict.copy()
        queryDict, serializerParams, querysetParams = self.get_shared_non_query_keys(mutableQD)
        queryDict, tmp1, tmp2 = self.get_non_query_keys(queryDict)
        serializerParams.update(tmp1)
        querysetParams.update(tmp2)

        return queryDict, serializerParams, querysetParams

    def bad_request(self, message):
        # first param should be an error page, but we don't have one yet
        # TODO: See
        # docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpResponseBadRequest
        # on how to make one. The parameter is the redirect link.
        response = django.http.HttpResponseBadRequest("/query")
        response.data = message
        return response

    def get(self, request, *args, **kwargs):
        queryDict, serializerParams, querysetParams = self.extract_params(request.query_params)

        # unfortunately unpacking operators do not work on QueryDicts like
        # they do on dicts. Items will also return only the last element of
        # a key, if the key is a list. See link above. This is ok here because
        # we do not support OR queries on same fields yet. Additionally we can
        # modify keys here with additional query-related params, f.e.
        # add __icontains, if we want to.
        qparams = {key: value for key, value in queryDict.items()}

        # now we get whatever specifically optimized queryset we want to start
        # off from and then do all of the filtering we want.
        try:
            queryset = self.query(qparams, querysetParams)
        except FieldError as e:
            return self.bad_request(e.args)

        serializer = self.serializer_class(queryset, many=True, **serializerParams)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MetadataView(GenericTableView):
    queryset = Metadata.objects.all()
    serializer_class = MetadataSerializer

    def get_non_query_keys(self, queryDict, *args, **kwargs):
        querysetParams = {}
        querysetParams["getWcs"] = queryDict.pop("getWcs", False)

        # in case something about a get_queryset requires modifying serializer
        # in some way add that logic here. Here, for example, the user requested
        # "getWcs", which means our serializer's queryset needs to prefetch
        # the wcs's for performance reasons. See
        # django-rest-framework.org/api-guide/relations/#nested-relationships
        # but also that it needs to keep the WCS serializer in its field list
        # in order to display it properly. Former happens in get_queryset, the
        # latter in __init__ of a serializer - so we need to add them in both
        serializerParams = {}
        serializerParams["keepWcs"] = querysetParams["getWcs"]

        return queryDict, serializerParams, querysetParams

    def get_queryset(self, getWcs=False, *args, **kwargs):
        if getWcs:
            return self.queryset.prefetch_related("wcs")
        return self.queryset

    def is_sky_region_query(self, qparams):
        return any(["raLow" in qparams, "raHigh" in qparams,
                    "decLow" in qparams, "decHigh" in qparams])

    def query_sky_region(self, qparams, queryset=None):
        if not all(["raLow" in qparams, "raHigh" in qparams,
                    "decLow" in qparams, "decHigh" in qparams]):
            raise FieldError(
                "Insufficient sky region parameters were present. "
                "Requires `raLow`, `raHight`, `decLow` and `decHight` "
                "in decimal degrees."
            )

        # pop them out, so that if there are any leftover qparams we can still
        # query on them as a regular filter
        raLow, raHigh = float(qparams.pop("raLow")), float(qparams.pop("raHigh"))
        decLow, decHigh = float(qparams.pop("decLow")), float(qparams.pop("decHigh"))

        lowerRight = getXYZFromWcs(raLow, decLow)
        upperLeft = getXYZFromWcs(raHigh, decHigh)

        wcsqparams =  {
            "wcs__wcs_center_x__gte": upperLeft["x"],
            "wcs__wcs_center_x__lte": lowerRight["x"],
            "wcs__wcs_center_y__lte": upperLeft["y"],
            "wcs__wcs_center_y__gte": lowerRight["y"],
            "wcs__wcs_center_z__lte": upperLeft["z"],
            "wcs__wcs_center_z__gte": lowerRight["z"]
        }

        # if no pre-filtered queryset was given, use the default one
        if queryset is None:
            queryset = self.get_queryset(getWcs=True)

        # add filtering on WCS information
        queryset = queryset.filter(**wcsqparams)

        # return the queryset for further filtering.
        return queryset, qparams

    def query(self, qparams, querysetParams):
        queryset = self.get_queryset(**querysetParams)

        if self.is_sky_region_query(qparams):
            queryset, qparams = self.query_sky_region(qparams, queryset)
        elif qparams:
            queryset = queryset.filter(**qparams)

        return queryset.all()


class WcsView(GenericTableView):
    queryset = Wcs.objects.all()
    serializer_class = WcsSerializer

    def get_queryset(self, *args, **kwargs):
        return self.queryset

    def get_non_query_keys(self, queryDict, *args, **kwargs):
        # no-op
        return queryDict, {}, {}

    def query(self,  qparams, querysetParams):
        queryset = self.get_queryset(**querysetParams)
        if qparams:
            queryset = queryset.filter(**qparams)
        else:
            queryset = queryset.all()

        return queryset

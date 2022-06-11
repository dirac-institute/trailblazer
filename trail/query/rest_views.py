import django
from django.core.exceptions import FieldError

from rest_framework import mixins, status
from rest_framework.views import APIView
from rest_framework.response import Response

from upload.models import Metadata, Wcs
from query.serializers import MetadataSerializer, WcsSerializer


class GenericTableView(mixins.ListModelMixin, APIView):
    """
     GenericTableView that serves as an interface to provide one unify rest api query
     to different tables
    """

    queryset = None
    serializer_class = None

    def get_shared_non_query_keys(self, queryDict):
        """
        Extracts the keys and values not directly related to the query from the given query dict,
        and copies them into a queryset related parameter
        and serializer related parameter dictionaries.
        Extracts only those keys and values that are shared among all table views,
        such as fields or casesensitive

        Parameters
        ----------
        queryDict: django.QueryDict
            The queryDict converted from user inputs

        Returns
        -------
        serializerParams : Dictionary
            The dictionary containing all serializer related param specified by each table.
        querysetParams : Dictionary
            The dictionary containing all pre-processing related param specified by each table.

        """

        # parse out any serializer keys we need.
        serializerParams = {}
        serializerParams["fields"] = queryDict.pop("fields", None)

        # parse out any get_queryset keywords we want, f.e. casesensitive
        querysetParams = {}

        return queryDict, serializerParams, querysetParams

    def get_non_query_keys(self, queryDict):
        """
        Remove the keys and values not directly related to the queryDict.
        and copies them into a queryset related parameter
        and serializer related parameter dictionaries.

        Parameters
        ----------
        queryDict: django.QueryDict
            The queryDict converted from user inputs

        Returns
        -------
        queryDict : Dictionary
            The cleaned dictionary that only has fields related to the query for
            the table.
        serializerParams : Dictionary
            The dictionary containing all serializerParams that is not related to the query,
            but meant for the serializers.
        querysetParams : Dictionary
            The dictionary containing all querySet that is not related to the query,
            but meant for the prefetching/changing the field lookup types.
            See link for more in field lookups
            https://docs.djangoproject.com/en/4.0/ref/models/querysets/#field-lookups

        """
        # no-op, could be NotImplemented too, makes sense to assume no special
        # keys are allowed for a generic table view though
        return queryDict, {}, {}

    def extract_params(self, queryDict):
        """
        Remove and split fields in queryDict into a dict for only query related keys,
        a dict for serializers relate keys, and a dict for preprocess related keys

        Parameters
        ----------
        queryDict: django.QueryDict
            The queryDict converted from user inputs

        Returns
        -------
        queryDict : Dictionary
            The cleaned dictionary that only has fields related to the query for
            the table.
        serializerParams : Dictionary
            The dictionary containing all serializerParams that is not related to the query,
            but meant for the serializers.
        querysetParams : Dictionary
            The dictionary containing all querySet that is not related to the query,
            but meant for the prefetching/changing the field lookup types.
            See link for more in field lookups
            https://docs.djangoproject.com/en/4.0/ref/models/querysets/#field-lookups

        """

        # See https://docs.djangoproject.com/en/4.0/ref/request-response/#id1
        # Remove keys that do not belong to the query, but are still used, f.e.
        # 'fields' or 'casesensitive'. Make a mutable copy first, then pop
        # always returns a list. Note the pop method supports default key, but
        # isn't documented. We need a copy to be mutable, see link.
        mutableQD = queryDict.copy()
        queryDict, serializerParams, querysetParams = self.get_non_query_keys(mutableQD)

        return queryDict, serializerParams, querysetParams

    def bad_request(self, message):
        """
        Helper for constructing a django.http.HttpResponseBadRequest
        with given message

        Parameters
        ----------
        message : String
            The message that we need to put into the bad request

        Returns
        -------
        response : django.http.HttpResponseBadRequest
            The bad request containing the message given.

        """

        # first param should be an error page, but we don't have one yet
        # TODO: See
        # docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpResponseBadRequest
        # on how to make one. The parameter is the redirect link.

        response = django.http.HttpResponseBadRequest("/query")
        response.data = message
        return response

    def get(self, request):
        """
        Generic get method for REST api, given request.params, it queries
        on the given querySet and serialize result back to the user.

        Parameters
        ----------
        request: Http.request
            The http reuqest sent.

        Returns
        -------
        response: Http.Response
            Return the query result in JSON format.

        Note
        -----
        If given request doesn't contain all keys needed, it will raise an exception.
        """

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
        except (FieldError, ValueError) as e:
            return self.bad_request(e.args)

        serializer = self.serializer_class(queryset, many=True, **serializerParams)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MetadataView(GenericTableView):
    queryset = Metadata.objects.all()
    serializer_class = MetadataSerializer

    def get_non_query_keys(self, queryDict):
        """
            Follows the same logic as GenericTableView.get_non_query_keys

        """

        querysetParams = {}
        querysetParams["getWcs"] = queryDict.get("getWcs", False)
        queryDict.pop("getWcs", False)
        querysetParams["exactMatch"] = queryDict.get("exactMatch", False)
        queryDict.pop("exactMatch", False)

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
        serializerParams["fields"] = queryDict.pop("fields", None)

        return queryDict, serializerParams, querysetParams

    def get_queryset(self, getWcs=False, *args, **kwargs):
        """
        Return the queryset for metatable table

        Parameters
        ----------
        getWcs: boolean
            whether to embed all wcs objects in the metadata query set.

        Returns
        -------
        queryset: Django QuerySet
            Returns the querySet for metadata table.

        """
        if getWcs:
            return self.queryset.prefetch_related("wcs")
        return self.queryset

    def is_sky_region_query(self, qparams):
        """
            Helper function for describing if the query is a query base on
            sky area.
        """
        return any(["raLow" in qparams, "raHigh" in qparams,
                    "decLow" in qparams, "decHigh" in qparams])

    def query(self, qparams, querysetParams):
        """
        Query the metadata table with the given query params

        Parameters
        ----------
        qparams: Dictionary
            The cleaned user given query dictionary
        querysetParams: Dictionary
            The extracted pre-processing indicator fields dictionary

        Returns
        -------
        queryset: Django QuerySet
            Returns the querySet containing all objects that match the query

        Notes
        -----
        if nothing is specified in the qparam, the method return all metadata by default.

        """
        queryset = self.get_queryset(**querysetParams)

        if self.is_sky_region_query(qparams):
            queryset, qparams = Metadata.query_sky_region(qparams, queryset)

        if qparams:
            if querysetParams["exactMatch"] == 'False':
                qparams = {key + "__icontains": val for key, val in qparams.items()}
            queryset = queryset.filter(**qparams)

        return queryset.all()


class WcsView(GenericTableView):
    queryset = Wcs.objects.all()
    serializer_class = WcsSerializer

    def get_queryset(self, *args, **kwargs):
        """
            Follows the same logic as MetadataView.get_queryset
        """
        return self.queryset

    def get_non_query_keys(self, queryDict, *args, **kwargs):
        """
            No op
        """
        return queryDict, {}, {}

    def query(self,  qparams, querysetParams):
        """
            Follows the same logic as MetadataView.query
        """
        queryset = self.get_queryset(**querysetParams)
        if qparams:
            queryset = queryset.filter(**qparams)
        else:
            queryset = queryset.all()

        return queryset

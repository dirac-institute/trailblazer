from django import forms
from django.shortcuts import render
from rest_framework.views import APIView
from upload.models import Metadata
from upload.models import Wcs
from upload.serializers import MetadataSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from django.db.models import Q
from django.db.models import F


class MetadataForm(forms.Form):

    """Defines the variables corresponding to the metadata columns.
    """
    unique_instrument = ["DECam", "ff09", "Imager on SDSS 2.5m"]
    # TODO: add more instruments once we support them
    u_instrlist = list((name, name) for name in unique_instrument)
    instrument = forms.CharField(max_length=20, widget=forms.Select(choices=u_instrlist))
    telescope = forms.CharField(max_length=20, required=False)
    processor_name = forms.CharField(max_length=20, required=False)
    obs_lon = forms.CharField(max_length=20, required=False)

    def get_query(self, casesensitive=True):
        new_dict = {}
        for key in self.data:
            if self.data[key] and key != 'csrfmiddlewaretoken':
                if casesensitive:
                    keyk = key + "__contains"
                    new_dict[keyk] = self.data[key]
                elif not casesensitive:
                    keyk = key + "__icontains"
                    new_dict[keyk] = self.data[key]
        return new_dict


def index(request):
    """Index renders the form when root url is visited, bypassing slower checks
    required fo rendering of the results url, where rendering of the table and
    checking for results are performed.

    It is assumed the request type is GET.
    """
    form = MetadataForm()
    return render(request, "query.html", {"queryform": form, "render_table": False})


def print_results(request):
    """Renders the results url, which is a placeholder copy of the root url of
    query interface, where any results are rendered alongside the table headers.
    """
    if request.method == "POST":
        form = MetadataForm(request.POST)
        if form.is_valid():
            query_results = Metadata.objects.filter(**form.get_query())
            wcs_list = []
            for obj in query_results:
                wcs_info = obj.wcs_set.all()
                wcs_list.append(wcs_info)

    else:
        query_results = []
        form = MetadataForm()
        wcs_list = []

    return render(request, "query.html",
                  {"data": query_results, "wcsdata": wcs_list, "queryform": form, "render_table": True})


class MetadataDAO(APIView):
    """
     Data Accessing objects for metadata, all query for metadatas are implemented here

    """

    RALOW = "raLow"
    RAHIGH = "raHigh"
    DECLOW = "decLow"
    DECHIGH = "decHigh"
    JOINPARAMS = "metadataParams"

    def queryJoinWcsAndMetadataParam(self, paramDict):
        """
        Returns the Metadata entries that meets both of the sky specified and the params given by the user

        Parameters
        ----------
        raLow: float
            the lower bound for ra
        raHigh: float
            the upper bound for ra
        decLow: float
            the lower bound for dec
        decHigh: float
            the upper bound for dec
        params: Dictionary
            the dictionary in the paramDict that contains the criterias for metadata object  Ex.(id = 3, processName=fits)
        
        

        Returns
        -------
        results: list of metadata objects
            a list of metadata objects that matches the param specified by users and is in the boundary box.

        Note
        -----
        If users do not specify a dict, the method will return all metadatas.
        If users do not specify a params, no metadata would be return.
        """
        if self.isWcsQueryParamMissing(paramDict):
            return []

        lowerRight = self.getXYZFromWcs(float(paramDict.get(self.RALOW)),
                                        float(paramDict.get(self.DECLOW)))
        upperLeft = self.getXYZFromWcs(float(paramDict.get(self.RAHIGH)),
                                       float(paramDict.get(self.DECHIGH)))

        skyBoundary = self.makeFilterDictForWcs(upperLeft, lowerRight)
        joinQuery = self.makeJoinQueryForReverseLookup(skyBoundary, paramDict.get(self.JOINPARAMS))
        filteredWcs = Wcs.objects.all().filter(**joinQuery)
        metadataIds = set([metadataId['metadata'] for metadataId in filteredWcs.values('metadata')])
        metadatas = self.getMetadatasByIds(metadataIds)
        return metadatas

    def queryByParams(self, paramDict):

        """
        Returns the Metadata entries that meets the users input

        Parameters
        ----------
        queryParam: dictionary
            List of criterias for metadata

        Returns
        -------
        results: list of metadata objects
            a list of metadata objects that matches the param specified by users.

        Notes
        -----
        If users do not specify a dict, the method will return all metadats
        """

        querySet = Metadata.objects.all()
        if paramDict is not None:
            querySet = querySet.filter(**paramDict)

        return list(querySet)

    def queryBySpecifiedSky(self, paramDict):

        """
        Returns the Metadata associated with the part of sky the user specifies

        Parameters
        ----------------
        raLow: float
            the lower bound for ra
        raHigh: float
            the upper bound for ra
        decLow: float
            the lower bound for dec
        decHigh: float
            the upper bound for dec

        Returns
        -------
        metadatas: list
            list of metadatas that is in the part of sky specified by the users

        Notes
        -------------------
        if the parameters is not specified correctly, will return an empty list

        """
        if self.isWcsQueryParamMissing(paramDict):
            return []

        lowerRight = getXYZFromWcs(float(paramDict.get(self.RALOW)),
                                   float(paramDict.get(self.DECLOW)))
        upperLeft = getXYZFromWcs(float(paramDict.get(self.RAHIGH)),
                                  float(paramDict.get(self.DECHIGH)))

        filteredWcs = Wcs.objects.all().filter(**self.makeFilterDictForWcs(upperLeft, lowerRight))
        # for every wcs, find the metadata id
        metadataIds = set([metadataId['metadata'] for metadataId in filteredWcs.values('metadata')])
        metadatas = self.getMetadatasByIds(metadataIds)

        return metadatas

    # Helpers -----------------------------------------
    def makeJoinQueryForReverseLookup(self, skyBoundary, paramDict):

        result = dict()
        for key, val in paramDict.items():
            result["metadata__" + key] = val
        
        result.update(skyBoundary)

        return result

    def getMetadatasByIds(self, metadataIds):
        """
        Helper function for getting metadata objects that matches the ids specified

        Parameters
        ----------
        metadaIds: list
            A list of metadata id that we need to fetch
        """
        result = []
        for id in metadataIds:
            result.append(Metadata.objects.get(id=id))
        return result

    def makeFilterDictForWcs(self, upperLeft, lowerRight):
        """
        Helper function for putting the sky boundary into a dictionary
        that could be pass into querySet.filter()

        Parameters
        ----------
        upperLeft: dictonary
            The upper left boundary for the sky specified
        lowerRight: dictionary
            The lower right boundary for the sky specified

        Return
        ------
        Dictionary
            A query dictionary that goes can go into the querySet.filter function
        """

        #TODO change the dict to use Q and F to find either center pixel is in the box,
        # or if the center pixel is within distance r with the boundary points
        return {
                "wcs_center_x__gte": upperLeft["x"],
                "wcs_center_x__lte": lowerRight["x"],
                "wcs_center_y__lte": upperLeft["y"],
                "wcs_center_y__gte": lowerRight["y"],
                "wcs_center_z__lte": upperLeft["z"],
                "wcs_center_z__gte": lowerRight["z"]
                }

    def isWcsQueryParamMissing(self, queryParams):
        """
        Check if the sky boundary is correctly specified

        Parameters
        ----------
        queryParams: Dictionary
            A dictionary that contains the boundary for the sky

        Return
        ------
        Return true if any of the param needed is not there
        """
        return not (self.RALOW in queryParams and self.RAHIGH in queryParams
                    and self.DECHIGH in queryParams and self.DECLOW in queryParams)


class MetadataQuery(APIView):

    """
    Support Query that returns metadata entry as a result through metadata info

    Attributes
    ----------
    metadataDao: MetadataDao
        Data accessing objects for metadata table

    """

    DATA_FIELDS = "fields"

    def __init__(self):
        self.metadataDao = MetadataDAO()

    # gets all the metadata entry that matches the query parameters.
    @swagger_auto_schema(responses={200: MetadataSerializer(many=True)})
    def get(self, request):

        """
        Returns the Metadata entries that meets the users input in json

        Parameters
        ----------
        fields: List of strings that is the key of wanted string
            list of wanted field in the metadata returned
        queryParam: Dictionary
            list of criterias for metadatas specified by users

        Return
        ------
        A json response that contains the list of metadatas wanted

        """
        fields = request.query_params.getlist(self.DATA_FIELDS)

        queryParams = request.query_params.dict()
        queryParams.pop(self.DATA_FIELDS, None)
        results = self.metadataDao.queryByParams(queryParams)
        if len(fields) == 0:
            fields = None

        result = MetadataSerializer(results, many=True, fields=fields)

        return Response(result.data, status=status.HTTP_200_OK)


class WcsQuery(APIView):
    """
    Support Query that returns metadata entry that is in the part of sky specified by the users.

    Attributes
    ----------
    metadataDao: MetadataDao
        Data accessing objects for metadata table

    """

    def __init__(self):
        self.metadataDao = MetadataDAO()

    def get(self, request):

        """
        Returns the Metadata associated with the part of sky the user specifies

        Parameters
        ----------------
        raLow: the lower bound for ra
        raHigh: the upper bound for ra
        decLow: the lower bound for dec
        decHigh: the upper bound for dec

        Notes
        -------------------
        if the parameters is not specified correctly, will return a bad request
        """
        metadatas = self.metadataDao.queryBySpecifiedSky(request.query_params)
        serializedMetadata = MetadataSerializer(metadatas, many=True)

        return Response(
                            serializedMetadata.data,
                            status=status.HTTP_200_OK,
                        )

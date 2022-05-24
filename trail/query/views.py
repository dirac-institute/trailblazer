from django import forms
from django.shortcuts import render
from rest_framework.views import APIView
from upload.models import Metadata
from upload.models import Wcs
import numpy as np
from upload.serializers import MetadataSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema


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

        Note
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
        raLow: the lower bound for ra
        raHigh: the upper bound for ra
        decLow: the lower bound for dec
        decHigh: the upper bound for dec

        Returns
        -------
        metadatas: list
            list of metadatas that is in the part of sky specified by the users

        Note
        -------------------
        if the parameters is not specified correctly, will return an empty result

        """
        if self.isWcsQueryParamMissing(paramDict):
            return []

        lowerRight = self.getXYZFromWcs(float(paramDict.get(self.RALOW)),
                                        float(paramDict.get(self.DECLOW)))
        upperLeft = self.getXYZFromWcs(float(paramDict.get(self.RAHIGH)),
                                       float(paramDict.get(self.DECHIGH)))

        filteredWcs = Wcs.objects.all().filter(**self.makeFilterDictForWcs(upperLeft, lowerRight))
        # for every wcs, find the metadata id
        metadataIds = set([metadataId['metadata'] for metadataId in filteredWcs.values('metadata')])
        metadatas = self.getMetadatasByIds(metadataIds)

        return metadatas

    def getMetadatasByIds(self, metadataIds):
        """
        Helper function for getting metadata objects that matches the ids specified

        """
        result = []
        for id in metadataIds:
            result.append(Metadata.objects.get(id=id))
        return result

    def makeFilterDictForWcs(self, upperLeft, lowerRight):
        """
        Helper function for putting the sky boundary into a dictionary that could be pass into querySet.filter()

        """
        return {
                "wcs_center_x__gte": upperLeft["x"],
                "wcs_center_x__lte": lowerRight["x"],
                "wcs_center_y__lte": upperLeft["y"],
                "wcs_center_y__gte": lowerRight["y"],
                "wcs_center_z__lte": upperLeft["z"],
                "wcs_center_z__gte": lowerRight["z"]
                }

    def getXYZFromWcs(self, ra, dec):
        """
        Convert ra and dec into xyz coordinates

        """
        x = np.cos(dec) * np.cos(ra)
        y = np.cos(dec) * np.sin(ra)
        z = np.sin(dec)

        return {"x": x, "y": y, "z": z}

    def isWcsQueryParamMissing(self, queryParams):
        """
        Check if the sky boundary is correctly specified

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

        Note
        -------------------
        if the parameters is not specified correctly, will return a bad request
        """
        metadatas = self.metadataDao.queryBySpecifiedSky(request.query_params)
        serializedMetadata = MetadataSerializer(metadatas, many=True)

        return Response(
                            serializedMetadata.data,
                            status=status.HTTP_200_OK,
                        )

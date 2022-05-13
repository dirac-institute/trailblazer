from django import forms
from django.shortcuts import render
from rest_framework.views import APIView
from upload.models import Metadata
from upload.models import Wcs
from upload.serializers import MetadataSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
import numpy as np

METADATA_COLS = set([
                        "id", "processor_name",
                        "instrument", "telescope",
                        "science_program",
                        "obs_lon", "obs_lat",
                        "obs_height", "datetime_begin",
                        "datetime_end", "exposure_duration",
                        "upload_info_id", "filter_name",
                        "standardizer_name"
                    ])


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


# gets all the metadata entry that looks at a certain part of the sky
class WcsQuery(APIView):

    RALOW = "raLow"
    RAHIGH = "raHigh"
    DECLOW = "decLow"
    DECHIGH = "decHigh"

    def get(self, request):

        """
        Returns the Metadata associated with the part of sky the user specifies
        ----------

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
        if self.isWcsQueryParamMissing(request.query_params):
            return Response({"error": "invalid reqeust"}, status=status.HTTP_404_NOT_FOUND)

        lowerRight = self.getXYZFromWcs(float(request.query_params.get(self.RALOW)),
                                        float(request.query_params.get(self.DECLOW)))
        upperLeft = self.getXYZFromWcs(float(request.query_params.get(self.RAHIGH)),
                                       float(request.query_params.get(self.DECHIGH)))
        filteredWcs = Wcs.objects.all().filter(**self.makeFilterDictForWcs(upperLeft, lowerRight))
        # for every wcs, find the metadata id
        metadataIds = set([metadataId['metadata'] for metadataId in filteredWcs.values('metadata')])
        metadatas = self.getMetadatasByIds(metadataIds)
        serializedMetadata = MetadataSerializer(metadatas, many=True)

        return Response(
                            serializedMetadata.data,
                            status=status.HTTP_200_OK,
                        )

    def getMetadatasByIds(self, metadataIds):
        result = []
        for id in metadataIds:
            result.append(Metadata.objects.get(id=id))
        return result

    def makeFilterDictForWcs(self, upperLeft, lowerRight):
        return {
                "wcs_center_x__gte": upperLeft["x"],
                "wcs_center_x__lte": lowerRight["x"],
                "wcs_center_y__lte": upperLeft["y"],
                "wcs_center_y__gte": lowerRight["y"],
                "wcs_center_z__lte": upperLeft["z"],
                "wcs_center_z__gte": lowerRight["z"]
                }

    def getXYZFromWcs(self, ra, dec):
        x = np.cos(dec) * np.cos(ra)
        y = np.cos(dec) * np.sin(ra)
        z = np.sin(dec)

        return {"x": x, "y": y, "z": z}

    def isWcsQueryParamMissing(self, queryParams):
        return not (self.RALOW in queryParams and self.RAHIGH in queryParams
                    and self.DECHIGH in queryParams and self.DECLOW in queryParams)


class MetadataQuery(APIView):

    """Support Query that returns metadata entry as a result through metadata info



    Notes
    -----
    """

    DATA_FIELDS = "fields"

    # gets all the metadata entry that matches the query parameters.
    @swagger_auto_schema(responses={200: MetadataSerializer(many=True)})
    def get(self, request):

        """
        Returns the Metadata entries that meets the users input
        Parameters
        ----------
        fields: list of wanted field in the metadata returned
        queryParam: list of criterias for metadata

        """
        fields = request.query_params.getlist(self.DATA_FIELDS)
        queryParams = request.query_params

        querySet = Metadata.objects.all()
        resultSet = None

        if request.query_params:
            for key, val in queryParams.items():
                if key in METADATA_COLS:
                    querySet = querySet.filter(**{key + "__icontains": val})

        resultSet = querySet

        if len(fields) == 0:
            fields = None

        result = MetadataSerializer(resultSet, many=True, fields=fields)

        return Response(result.data, status=status.HTTP_200_OK)

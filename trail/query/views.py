from django import forms
from django.shortcuts import render
from rest_framework.views import APIView
from upload.models import Metadata
from upload.models import Wcs
from upload.serializers import MetadataSerializer
from django.http import HttpResponse
from django.http import JsonResponse
from rest_framework import status
import numpy as np
import json

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


class MetadataQuery(APIView):
    DATA_RETURNCOLS = "returnCols"
    DATA_QUERYPARAM = "queryParams"
    DATA_RETURNALL = "returnAllCols"
    RALOW = "raLow"
    RAHIGH = "raHigh"
    DECLOW = "decLow"
    DECHIGH = "decHigh"

    # gets all the metadata entry that matches the query parameters.
    def post(self, request):
        returnAll = request.data[self.DATA_RETURNALL]
        returnCols = request.data[self.DATA_RETURNCOLS]
        queryParams = request.data[self.DATA_QUERYPARAM]

        querySet = Metadata.objects.all()
        resultSet = Metadata.objects.none()
        for queryParam in queryParams:
            # each one is a dict and it is or operation
            # "queryParams" : [{"observer" : "me", "location" : "seattle"}]
            iterationSet = querySet
            if not (returnAll == 1):
                iterationSet = iterationSet.filter(**queryParam).values(*returnCols)
            else:
                iterationSet = iterationSet.filter(**queryParam).values()
            resultSet = resultSet | iterationSet

        result = json.dumps(list(resultSet), default=str)
        return HttpResponse(result, content_type="application/json")

    # gets all the metadata entry that looks at a certain part of the sky
    # 
    def get(self, request):
        if self.isWcsQueryParamMissing(request.query_params):
            return JsonResponse({"error" : "invalid response"}, status=status.HTTP_404_NOT_FOUND)
        
        lowerRight = self.getXYZFromWcs(float(request.query_params.get(self.RALOW)), float(request.query_params.get(self.DECLOW)))
        upperLeft = self.getXYZFromWcs(float(request.query_params.get(self.RAHIGH)), float(request.query_params.get(self.DECHIGH)))

        filteredWcs = Wcs.objects.all().filter(**self.makeFilterDictForWcs(upperLeft, lowerRight))
        
        # for every wcs, find the metadata id
        metadataIds = set([metadataId['metadata'] for metadataId in filteredWcs.values('metadata')])
        metadatas = self.getMetadatasByIds(metadataIds)
        print(metadatas)
        serializedMetadata = MetadataSerializer(metadatas, many=True)

        return JsonResponse(
                            serializedMetadata.data, 
                            status=status.HTTP_200_OK, 
                            safe=False
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
        RALOW = "raLow"
        RAHIGH = "raHigh"
        DECLOW = "decLow"
        DECHIGH = "decHigh"

        return not (self.RALOW in queryParams and self.RAHIGH in queryParams
                and self.DECHIGH in queryParams and self.DECLOW in queryParams)

        
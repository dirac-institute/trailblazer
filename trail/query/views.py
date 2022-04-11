from django import forms
from django.apps import apps
from django.shortcuts import render
from rest_framework.views import APIView
from upload.models import Metadata
from django.http import HttpResponse
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

class MetaDataQuery(APIView):
    DATA_RETURNCOLS = "returnCols"
    DATA_QUERYPARAM =  "queryParams"
    DATA_RETURNALL = "returnAllCols"

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
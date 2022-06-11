from datetime import date
from django import forms
from django.shortcuts import render
from rest_framework.views import APIView
#from upload.models import Metadata
#from upload.models import Wcs
from django.apps import apps
from upload.serializers import MetadataSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from coordinates import getXYZFromWcs
from django.http import HttpResponse
from django.contrib import messages
from django.template import Library
from urllib3 import HTTPResponse
from django_tables2 import SingleTableView
from .query_table import QueryTable
import csv
from astropy import units as u
from astropy.coordinates import SkyCoord

Metadata = apps.get_model('upload', 'Metadata')
Wcs = apps.get_model('upload', 'Wcs')

class DateInput(forms.DateInput):
    input_type = 'date'

class MetadataForm(forms.Form):

    """Defines the variables corresponding to the metadata columns.
    """
    unique_instrument = Metadata.objects.values("instrument").distinct()
    #unique_instrument = [(i, obj["instrument"]) for i, obj in enumerate(unique_instrument)]
    unique_instrument = [(obj["instrument"], obj["instrument"]) for obj in unique_instrument]
    instrument = forms.CharField(max_length=20, widget=forms.Select(choices=unique_instrument))
    telescope = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Telescope'}), required=False)
    datetime_begin = forms.DateField(widget=DateInput, required=False)
    datetime_end =  forms.DateField(widget=DateInput, required=False)
    ra = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Right Ascension(°)'}), required=False)
    dec = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Declination(°)'}), required=False)
    box_size = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Box Size(u)'}), required=False)
    lon = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Longitude'}), required=False)
    lat = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Lattitude'}), required=False)
    obs_height = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Observatory Height (m)'}), required=False)
    unique_filter = Metadata.objects.values("filter_name").distinct()
    uniqfilt = []
    for i, obj in enumerate(unique_filter):
        if obj["filter_name"] == "":
            uniqfilt.append((i, "Unknown"))
        else:
            uniqfilt.append((i, obj["filter_name"]))
    #filter_name = forms.CharField(max_length=20, widget=forms.Select(choices=uniqfilt))

    # def __init__(self, *args, **kwargs):
    #     super(MetadataForm, self).__init__(*args, **kwargs)
    #     self.fields['dec'].widget.attrs['style']  = 'placeholder=\"Right Ascension(°)\";'
    #     # self.fields['box_size'].widget.attrs['style']  = 'width:15%;'
    #     # self.fields['ra'].widget.attrs['style']  = 'width:15%;'
    #     # self.fields['datetime_begin'].widget.attrs['style']  = 'float: left;'
    #     # self.fields['datetime_end'].widget.attrs['style']  = 'float: left;'
    def get_query(self, casesensitive=True):
        new_dict = {}
        ra = ""
        dec = ""
        if self.data["ra"] != "" or self.data["dec"] != "":
            try:
                ra = float(self.data["ra"])
                dec = float(self.data["dec"])
            except ValueError:
                print("Error Found")
                return new_dict
            coordinates = SkyCoord(ra=ra*u.degree, dec=dec*u.degree)
            print("Answer Below")
            print(coordinates.cartesian.x)
            print(coordinates.cartesian.y)
            print("_______")
            ra = coordinates.cartesian.x
            dec = coordinates.cartesian.y
            # new_dict["filter_name__contains"] = self.uniqfilt[int(self.data["filter_name"])][1]
        for key in self.data:
            if self.data[key] and key != 'csrfmiddlewaretoken':
                if key == "box_size":
                    continue
                if casesensitive:
                    if key == "ra":
                        key = "obs_lon__contains"
                        new_dict[key] = ra
                    elif key == "dec":
                        key = "obs_lat__contains"
                        new_dict[key] = dec
                    else:
                        keyk = key + "__contains"
                        new_dict[keyk] = self.data[key]
                elif not casesensitive:
                    if key == "ra":
                        key = "obs_lon__icontains"
                        new_dict[key] = ra
                    elif key == "dec":
                        key = "obs_lat__icontains"
                        new_dict[key] = dec
                    else:
                        keyk = key + "__icontains"
                        new_dict[keyk] = self.data[key]
        return new_dict
curForm =  None
def index(request):
    """Index renders the form when root url is visited, bypassing slower checks
    required fo rendering of the results url, where rendering of the table and
    checking for results are performed.

    It is assumed the request type is GET.
    """
    form = MetadataForm()
    return render(request, "query.html", {"queryform": form, "show_table": False,
    "table": ""})


class ObservatonView(SingleTableView):
    model = Metadata
    table_class = QueryTable
    template_name = 'templates/query.html'

def print_results(request):
    """Renders the results url, which is a placeholder copy of the root url of
    query interface, where any results are rendered alongside the table headers.
    """
    if request.method == "POST":
        form = MetadataForm(request.POST)
        global curForm
        curForm = form
        if form.is_valid():
            MDAO = MetadataDAO()
            rform = form.get_query()
            query_results = MDAO.queryByParams(rform)
            if len(rform) == 0:
                messages.error(request, "Invalid Entry. Please check values again")
                query_results = []
            elif len(query_results) == 0:
                 messages.error(request, "No Results found")
            else:
                for i in query_results:
                    i.obs_lon = round(i.obs_lon, 2)
                    i.obs_lat = round(i.obs_lat, 2)
                    i.obs_height = round(i.obs_height, 2)
                    if i.filter_name == "":
                        i.filter_name = "Unknown"
            wcs_list = []
            for obj in query_results:
                wcs_info = obj.wcs_set.all()
                wcs_list.append(wcs_info)
            table =  QueryTable(query_results)
    else:
        messages.error(request, "Invalid Entry. Please check values again")
        query_results = []
        form = MetadataForm()
        wcs_list = []

    return render(request, "query.html",
                  {"data": query_results, "wcsdata": wcs_list, "table": table,
                  "queryform": form, "show_table": True})


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

        Notes
        -----
        If users do not specify a dict, the method will return all metadats
        """

        querySet = Metadata.objects.all()
        if paramDict is not None:
            querySet = querySet.filter(**paramDict)

        return querySet

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

def download_query(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="query.csv"'
    global curForm
    query_results = None
    if curForm.is_valid():
            MDAO = MetadataDAO()
            query_results = MDAO.queryByParams(curForm.get_query()).all().values_list('instrument','telescope', 'datetime_begin', 'datetime_end', 'exposure_duration', 'obs_lon', 'obs_lat', 'obs_height', 'filter_name')
    writer = csv.writer(response)
    writer.writerow(['INSTRUMENT NAME','TELESCOPE', 'UTC AT EXPOSURE START', 'UTC AT EXPOSURE END', 'EXPOSURE TIME (S)', 'OBSERVATORY LONGITUDE (DEG)', 'OBSERVATORY LATITUDE (DEG)', 'OBSERVATORY HEIGHT (M)', 'FILTER NAME'])
    fields = query_results
    for field in fields:
        writer.writerow(field)
    return response
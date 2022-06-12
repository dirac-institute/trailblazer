from django import forms, apps
from django.contrib import messages
from django.shortcuts import render

import astropy.units as u

from .rest_views import MetadataView
from .query_table import QueryTable

Metadata = apps.apps.get_model('upload', 'Metadata')
Wcs = apps.apps.get_model('upload', 'Wcs')


class DateInput(forms.DateInput):
    input_type = 'date'


class MetadataForm(forms.Form):
    """The query form containing 3 distinct sections in which users can select
    their query parameters:
    * the date range query
    * the sky region selection
    * the observatory parameters
    * the instrument parameters
    """

    unique_instrument = Metadata.objects.values("instrument").distinct()
    unique_instrument = [(obj["instrument"], obj["instrument"]) for obj in unique_instrument]
    unique_instrument.insert(0, ("Any", "Any"))
    instrument = forms.CharField(
        max_length=20,
        widget=forms.Select(choices=unique_instrument),
        label="Instrument"
    )

    telescope = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Telescope'}),
        required=False,
        label="Telescope"
    )

    datetime_begin = forms.DateField(
        widget=DateInput,
        required=False,
        label="Start date"

    )
    datetime_end = forms.DateField(
        widget=DateInput,
        required=False,
        label="End date"
    )

    ra = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Right Ascension(°)'}),
        required=False,
        label="Right Ascension"
    )
    dec = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Declination(°)'}),
        required=False,
        label="Declination"
    )
    box_size = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Box Size(u)'}),
        required=False,
        label="Box Size"
    )

    lon = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Longitude'}),
        required=False,
        label="Longitude"
    )
    lat = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Latitude'}),
        required=False,
        label="Latitude"
    )

    unique_filter = Metadata.objects.values("filter_name").distinct()
    unique_filter = [(f["filter_name"], f["filter_name"]) for f in unique_filter]
    unique_filter.insert(0, ("Any", "any"))
    unique_filter.insert(0, ("Unknown", ""))
    filter_name = forms.CharField(
        max_length=20,
        widget=forms.Select(choices=unique_filter),
        required=False
    )

    def calc_bbox(self, ra, dec, size):
        ra = ra*u.degree
        dec = dec*u.degree
        size = size*u.arcsecond

        raLow = ra.to(u.rad) - size.to(u.rad)/2
        raHigh = ra.to(u.rad) + size.to(u.rad)/2
        decLow = dec.to(u.rad) - size.to(u.rad)/2
        decHigh = dec.to(u.rad) + size.to(u.rad)/2

        return raLow, raHigh, decLow, decHigh

    def get_sky_region_data(self, qparams):
        ra = self.data.get("ra", False)
        dec = self.data.get("dec", False)
        size = self.data.get("box_size", False)

        if all([ra, dec, size]):
            raLow, raHigh, decLow, decHigh = self.calc_bbox(ra, dec, size)
            qparams["raLow"] = raLow
            qparams["raHigh"] = raHigh
            qparams["decLow"] = decLow
            qparams["decHigh"] = decHigh

        return qparams

    def get_date_range_data(self, qparams):
        start = self.data.get("datetime_begin", False)
        end = self.data.get("datetime_end", False)

        if start:
            qparams["datetime_begin__gte"] = start
        if end:
            qparams["datetime_end__lte"] = end

        return qparams

    def get_instrument_data(self, qparams):
        instrument = self.data.get("instrument", False)
        if instrument == "Any":
            # for us no value query means all values
            return qparams
        else:
            qparams["instrument"] = instrument

        return qparams

    def get_telescope_data(self, qparams):
        telescope = self.data.get("telescope", False)
        if telescope:
            qparams["telescope"] = telescope
        return qparams

    def get_observatory_location(self, qparams):
        lat = self.data.get("lat", False)
        lon = self.data.get("lon", False)

        if lat:
            qparams["obs_lat__lte"] = float(lat) + 1
            qparams["obs_lat__gte"] = float(lat) - 1
        if lon:
            qparams["obs_lon__lte"] = float(lon) + 1
            qparams["obs_lon__gte"] = float(lon) - 1

        return qparams

    def get_query_parameters(self, exactMatch=False):
        qparams = {}
        qparams = self.get_sky_region_data(qparams)
        qparams = self.get_date_range_data(qparams)
        qparams = self.get_instrument_data(qparams)
        qparams = self.get_telescope_data(qparams)
        qparams = self.get_observatory_location(qparams)
        return qparams


def index(request):
    """Index renders the form when root url is visited, bypassing slower checks
    required fo rendering of the results url, where rendering of the table and
    checking for results are performed.

    It is assumed the request type is GET.
    """
    form = MetadataForm()
    return render(
        request, "query.html",
        {"queryform": form,
         "show_table": False,
         "table": None}
    )


def print_results(request, exactMatch=False):
    """Renders the results url, which is a placeholder copy of the root url of
    query interface, where any results are rendered alongside the table headers.
    """

    if request.method == "POST":
        form = MetadataForm(request.POST)
        if form.is_valid():
            qparams = form.get_query_parameters()
            query_results = MetadataView().query(
                qparams,
                {"exactMatch": exactMatch}
            )
            show_table = True
            table = QueryTable(query_results)
    else:
        messages.error(request, "Invalid Entry. Please check values again")
        form = MetadataForm()
        show_table = False
        table = None

    return render(
        request, "query.html",
        {"queryform": form,
         "show_table": show_table,
         "table": table, }
    )


# def download_query(request):
#    response = HttpResponse(content_type='text/csv')
#    response['Content-Disposition'] = 'attachment; filename="query.csv"'
#    global curForm
#    query_results = None
#    if curForm.is_valid():
#            MDAO = MetadataDAO()
#            query_results = MDAO.queryByParams(curForm.get_query())
# .all().values_list('instrument','telescope', 'datetime_begin',
# 'datetime_end', 'exposure_duration', 'obs_lon', 'obs_lat', 'obs_height',
# 'filter_name')
#    writer = csv.writer(response)
#    writer.writerow(['INSTRUMENT NAME','TELESCOPE', 'UTC AT EXPOSURE START',
# 'UTC AT EXPOSURE END', 'EXPOSURE TIME (S)', 'OBSERVATORY LONGITUDE (DEG)',
# 'OBSERVATORY LATITUDE (DEG)', 'OBSERVATORY HEIGHT (M)', 'FILTER NAME'])
#    fields = query_results
#    for field in fields:
#        writer.writerow(field)
#    return response

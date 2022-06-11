from datetime import date
from django import forms
from django.shortcuts import render

from upload.models import Metadata


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
                  {"data": query_results, "wcsdata": wcs_list, "queryform": form, "render_table": True})

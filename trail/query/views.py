from django import forms
# from django.forms import ModelForm
from django.apps import apps
from django.shortcuts import render


Metadata = apps.get_model('upload', 'Metadata')
# Needs to think about adding SELECT DISTINCT etc.


class MetadataForm(forms.Form):
    """Defines the variables corresponding to the metadata columns.
    """
    unique_instrument = ["DECam", "ff09", "Imager on SDSS 2.5m"]
    # TODO: add more instruments once we support them
    u_instrlist = list((name, name) for name in unique_instrument)
    instrument = forms.CharField(max_length=20, widget=forms.Select(choices=u_instrlist))
    telescope = forms.CharField(max_length=20, required=False)
    processor_name = forms.CharField(max_length=20, required=False)


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
            query_results = Metadata.objects.filter(instrument__icontains=form.data["instrument"])
    else:
        query_results = []
        form = MetadataForm()
    return render(request, "query.html", {"data": query_results, "queryform": form, "render_table": True})

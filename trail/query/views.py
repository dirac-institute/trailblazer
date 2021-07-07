from django.apps import apps
# from django.http import HttpResponse
from django.shortcuts import render
from django.forms import ModelForm
from django.forms import BooleanField
from query.forms import Settings
from django_tables2 import SingleTableView
from .models import Observation
from .tables import ObservationTable

class ObservationListView(SingleTableView):
    model = Observation
    table_class = ObservationTable
    template_name = "query/observation.html"

class SettingsForm(ModelForm):
    receive_newsletter = BooleanField()


class Meta:
    model = Settings


# not used
def index(request):
    # return HttpResponse("Wouldn't it be nice if someone wrote a query tool here?")
    return render(request, "query.html")


Metadata = apps.get_model('upload', 'Metadata')

# This loads how the metadata database is structured
# Metadata = apps.get_model('upload', Metadata)


def print_results(request):
    """This function runs takes a request and renders some html on the query.html page."""
    # This is the django way of doing `select * from upload_metadata;
    emptylist = []
    if request.method == "POST":
        userdata = request.POST.get("Inst")
        query_result = Metadata.objects.filter(instrument__icontains=userdata)
  
        for item in query_result:
            itemDict = item.toDict()
            emptylist.append(itemDict)
    # breakpoint()
    return render(request, "query.html", {"data": emptylist})

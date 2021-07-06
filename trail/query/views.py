from django.http import HttpResponse


# not used
def index(request):
    return HttpResponse("Wouldn't it be nice if someone wrote a query tool here?")

from django.apps import apps
from django.shortcuts import render
# This loads how the metadata database is structured
Metadata = apps.get_model('upload', Metadata)
def print_results(request):
    """This function runs takes a request and renders some html on the query.html page.
    """
    # This is the django way of doing `select * from upload_metadata;`
    query_result = Metadata.all()
    return render(request, "query.html", {data: query_result})
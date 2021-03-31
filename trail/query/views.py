from django.http import HttpResponse


def index(request):
    return HttpResponse("Wouldn't it be nice if someone wrote a query tool here?")

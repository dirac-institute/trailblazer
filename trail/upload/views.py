"""This code runs when a user visits the 'upload' URL."""

from django.shortcuts import render
from django.http import JsonResponse

from upload.forms import UploadForm


def upload_view(request):
    """Renders the /uploads/ page.

    Parameters
    ----------
    request : `django.requst.HttpRequest`
        HTTP request made to the server.
    """
    if request.method == 'GET':
        form = UploadForm()
    else:
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            return JsonResponse({'action': 'replace', 'html': form.form_valid(request), })
        else:
            return JsonResponse({'action': 'replace', 'html': form.as_html(request), })

    return render(
        request,
        'upload.html', {
            'form': form,
            'form_as_html': form.as_html(request),
        }
    )

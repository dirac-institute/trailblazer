"""This code runs when a user visits the 'upload' URL."""

from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from .forms import FileFieldForm

# These uploads are required here so that the subclasses register themselves
from .process_uploads.processors import *
from .process_uploads.standardizers import *
from .process_uploads.upload_processor import UploadProcessor


def process_uploads(request):
    """Given a uploaded file, normalizes and inserts header data into the DB,
    creates and stores small and large thumbnails and saves a copy of the
    uploaded file.

    Parameters
    ----------
    request : `django.requst.HttpRequest`
        HTTP request made to the server.
    """
    processors = UploadProcessor.fromRequest(request)
    for processor in processors:
        processor.process()


class FileFieldView(FormView):
    form_class = FileFieldForm
    template_name = 'upload.html'
    success_url = reverse_lazy('upload')

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            process_uploads(request)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

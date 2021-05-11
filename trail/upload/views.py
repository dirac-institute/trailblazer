"""This code runs when a user visits the 'upload' URL."""

from django.urls import reverse_lazy 
from django.views.generic.edit import FormView
from .forms import FileFieldForm

# These uploads are required here so that the subclasses register themselves
from .process_uploads.processors import *
from .process_uploads.standardizers import *
from .process_uploads.view_functionality import process_uploads


class FileFieldView(FormView):
    form_class = FileFieldForm
    template_name = 'upload.html' 
    success_url = reverse_lazy('upload')

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file_field')
        if form.is_valid():
            process_uploads(files)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

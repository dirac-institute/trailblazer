# from django.shortcuts import render

from django.urls import reverse_lazy  # , reverse
from django.views.generic.edit import FormView
from .forms import FileFieldForm

from .process_uploads.process_fits import process_fits

"""This code runs when a user visits the 'upload' URL."""


class FileFieldView(FormView):
    form_class = FileFieldForm
    template_name = 'upload.html'  # Replace with your template.
    success_url = reverse_lazy('upload')  # Replace with your URL or reverse().

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file_field')
        if form.is_valid():
            for f in files:
                process_fits(f)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

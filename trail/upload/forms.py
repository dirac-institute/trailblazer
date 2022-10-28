"""Contains the upload form."""
import os

from django import forms
from django.template.loader import render_to_string

# These uploads are required here so that the subclasses register themselves
# and that can't be done in __init__ because django AppRegistryNotReady error
from .process_uploads.processors import *  # noqa: F403, F401
from .process_uploads.standardizers import *  # noqa: F403, F401
from .process_uploads.upload_processor import UploadProcessor


class UploadForm(forms.Form):
    """
    Upload form.

    Parameters
    ----------
    data : `django.QueryDict`
        Request body.
    files : `django.MultiValueDict`
        Dict-like object containing the uploaded files.
    kwargs : `dict`
        Keyword arguments are passed onto `django.forms.Form`.

    Attributes
    ----------
    data : `django.QueryDict`
        Request body.
    files : `django.MultiValueDict`
        Dict-like object containing the uploaded files.
    file_errors : `list`
        List of strings detailing the reasons why the file was rejected.
        Populated by `is_valid` method.
    accept: `str`
        A string stating the file extensions that are allowed.
        TODO: this should be a list and it should be used in the JS scripts,
        one of the `allowed_file_types` and `allowed` needs to be deprecated.
    allowed_file_types:
        Same as `accept` except for server-side validation.
    max_file_size_mb : `int`
        Maximum size of uploaded file.
    """

    class Media:
        css = {
            'all': ('assets/css/upload_form.css', )
        }
        js = (
            'assets/js/upload_form.js',
            'assets/js/upload_button_state.js',
            'assets/js/filelist.js',
        )

    def __init__(self, data=None, files=None, **kwargs):
        super().__init__(data, files, **kwargs)
        self.data = data
        self.files = files
        self.file_errors = []
        self.accept = None
        self.allowed_file_types = "fits"
        self.max_file_size_mb = 1000

    def form_valid(self, request):
        """
        Processes uploaded files and redirects to `get_success_url()`.

        Processing files consists of normalizing headers of selected files,
        creating thumbnails and saving the copies of the uploaded files.

        Parameters
        ----------
        request : `django.requst.HttpRequest`
            HTTP request made to the server.

        Returns
        -------
        success_report : `HtmlResponse`
            An HTML table displaying some basic success/fail processing status.
        """
        processors = UploadProcessor.fromRequest(request)
        results = []
        for processor in processors:
            results.append(processor.process())

        return self.get_success_report(request, results)

    def get_success_report(self, request, results):
        """Given the upload request and the results of processing renders the
        `upload_report.html` template as a string and returns it.

        Parameters
        ----------
        request : `django.requst.HttpRequest`
            HTTP request made to the server.
        results : `list[models.StandardizedResult]`
            List containing `models.StandardizedResult` instances.

        Returns
        -------
        report : `HtmlResponse`
            HTML string containing the report table.
        """
        report_data = []
        for res in results:
            report_data.append({
                "smallthumb": res.thumbnails[0].small,
                "wcsid": res.wcs[0].id,
                "processor": res.metadata.processor_name,
                "standardizer": res.metadata.standardizer_name,
                "obs_lon": round(res.metadata.obs_lon, 2),
                "obs_lat": round(res.metadata.obs_lat, 2),
                "datetime": res.metadata.datetime_begin
            })

        html = render_to_string(
            'upload_report.html', {
                'data': report_data,
            },
            request
        )

        return html

    def get_action(self, request=None):
        """HTML Form action attribute (the URL of the resource that processes
        the data, which in our case is handled by JS script).
        """
        return "/upload/"

    def get_accept(self):
        """Return the list of accepted file types."""
        return self.accept

    def get_max_file_size(self, request=None):
        """Return the maximum allowed file size in MB."""
        return self.max_file_size_mb

    def _list_allowed_file_types(self):
        """Tokenizes the allowed file types to allow variations of the allowed
        extensions.
        """
        text = self.allowed_file_types if self.allowed_file_types is not None else ""
        # Allow multiple separators
        tokens = text.lower().replace(',', ' ').replace(';', ' ').split()
        # Add leading dot when required
        tokens = [t if t.startswith('.') else ('.'+t) for t in tokens]
        return tokens

    def as_html(self, request):
        """Renders the form as an HTML string.

        Parameters
        ----------
        request : `django.requst.HttpRequest`
            HTTP request made to the server.
        """
        accept = self.get_accept()
        if accept is None:
            # Build from list of allowed file types
            accept = ','.join(self._list_allowed_file_types())

        html = render_to_string(
            'upload_form.html', {
                'form': self,
                'file_errors': self.file_errors,
                'action': self.get_action(request),
                'accept': accept,
                'max_file_size_mb': self.get_max_file_size(request)
            },
            request
        )

        return html

    def is_valid(self):
        """Checks if the form is valid.

        Form is valid if no files exceed the file size limit and if the files
        are of the allowed type. Form is also validated client-side in the JS
        scripts.

        Returns
        -------
        valid : `bool`
            True if the form is valid, False otherwise.
        """
        allowed_file_types = self._list_allowed_file_types()
        max_file_size_MB = self.get_max_file_size()

        self.file_errors = []
        files = self.files.getlist('files')
        for file in files:
            name, extension = os.path.splitext(file.name)
            extension = extension.lower()
            size_MB = file.size / (1024 * 1024)
            if extension not in allowed_file_types:
                self.file_errors.append(f"{file.name}: File type not allowed")
            if size_MB > max_file_size_MB:
                self.file_errors.append(f"{file.name}: File size exceeds {max_file_size_MB}MB.")

        # return len(self.file_errors) <= 0
        valid = super().is_valid() and len(self.file_errors) <= 0
        return valid

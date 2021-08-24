"""
Class that facilitates the processing of an uplod.
"""


from abc import ABC, abstractmethod
import logging

from django.conf import settings

from upload.models import UploadInfo
from .upload_wrapper import TemporaryUploadedFileWrapper


__all__ = ["UploadProcessor", "get_ip"]


logger = logging.getLogger(__name__)


def get_ip(request):
    """Given an HTTP request returns the originating IP address.

    Parameters
    ----------
    request : `django.requst.HttpRequest`
        HTTP Request made to the server.

    Returns
    -------
    ip : `str`
        IP Address.

    Notes
    -----
    IP addresses in HTTP requests can be spoofed.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class UploadProcessor(ABC):
    """Supports processing of a single uploaded file.

    Parameters
    ----------
    uploadInfo : `uploads.model.UploadInfo`
        Object containing the time and date of upload and originating IP.
    uploadedFile : `upload_wrapper.temporaryUploadedFileWrapper`
        Uploaded file.
    """

    processors = dict()
    """All registered upload processing classes."""

    name = None
    """Processor's name. Only named processors will be registered."""

    priority = 0
    """Priority. Processors with high priority are prefered over processors
    with low priority when processing an upload.
    """

    media_root = settings.MEDIA_ROOT
    """Root of the location where thumbnails will be stored."""

    @abstractmethod
    def __init__(self, uploadInfo, uploadedFile, *args, **kwargs):
        self.uploadInfo = uploadInfo
        self.uploadedFile = uploadedFile

    def __init_subclass__(cls, **kwargs):
        # Registers subclasses of this class with set `name` class parameters
        # as availible translators
        name = getattr(cls, "name", False)
        if name and name is not None:
            super().__init_subclass__(**kwargs)
            UploadProcessor.processors[cls.name] = cls

    @classmethod
    @abstractmethod
    def canProcess(self, uploadedFile):
        """Returns ``True`` when the processor knows how to process the given
        upload (file) type.

        Parameters
        ----------
        uploadedFile : `upload_wrapper.TemporaryUploadedFileWrapper.
            Uploaded file.

        Returns
        -------
        canProcess : `bool`
            `True` when the processor knows how to handle uploaded file and
            `False` otherwise

        Notes
        -----
        Implementation is instrument-specific.
        """
        raise NotImplementedError()

    @abstractmethod
    def process(self):
        """Process the given upload.

        Notes
        -----
        Implementation is processor-specific.
        """
        raise NotImplementedError()

    @classmethod
    def getProcessor(cls, uploadedFile):
        """Get the processor class that can handle given file. If multiple
        processors declare the ability to process the given file the
        processor with highest prirority is selected.

        Parameters
        ----------
        uploadedFile : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.

        Returns
        -------
        processor : `cls`
            Processor class that can process the given upload.
        """
        processors = []
        for processor in cls.processors.values():
            if processor.canProcess(uploadedFile):
                processors.append(processor)

        def get_priority(processor):
            """Return processors priority."""
            return processor.priority
        processors.sort(key=get_priority, reverse=True)

        if processors:
            if len(processors) > 1:
                # I think this should never be an issue really, but just in case
                names = [proc.name for proc in processors]
                logger.info("Multiple processors declared ability to process "
                            f"the given upload: {names}. Using {names[-1]} "
                            "to process FITS.")
            return processors[0]
        else:
            raise ValueError("None of the known processors can handle this upload.\n "
                             f"Known processors: {list(cls.processors.keys())}")

    @classmethod
    def fromFileWrapper(cls, uploadedFile, ip=None):
        """Return a single Processor that can process the file. If not given,
        the origin of upload is assumed to be coming from a local server.

        Parameters
        ----------
        uploadedFile : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.
        ip : `str`, optional
            Originating IP. Defaults to `localhost`.

        Returns
        -------
        processor : `object`
            Instance of a Processor class that can process the given upload.

        Raises
        ------
        ValueError
            None of the registered processors can process the upload.
        """
        uploadInfo = UploadInfo() if ip is None else UploadInfo(ip=ip)
        processorCls = cls.getProcessor(uploadedFile)
        return processorCls(uploadInfo, uploadedFile)

    @classmethod
    def fromRequest(cls, request):
        """Return Processor(s) that can process the request.

        Parameters
        ----------
        request : `django.requst.HttpRequest`
            HTTP Request made to the server.

        Returns
        -------
        processors : `list`
            List of Processors that can process the files given in the request.

        Raises
        ------
        ValueError
            None of the registered processors can process one of the uploads.
        """
        ip = get_ip(request)
        uploadInfo = UploadInfo(ip=ip)

        processors = []
        for uploadedFile in request.FILES.getlist("file_field"):
            uploadedFile = TemporaryUploadedFileWrapper(uploadedFile)
            processorCls = cls.getProcessor(uploadedFile)
            processors.append(processorCls(uploadInfo, uploadedFile))

        return processors

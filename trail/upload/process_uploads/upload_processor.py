"""
Class that facilitates the processing of an uplod.
"""


from abc import ABC, abstractmethod
import warnings

from django.conf import settings


__all__ = ["UploadProcessor", ]


class UploadProcessor(ABC):
    """Supports processing of a single uploaded file.

    Parameters
    ----------
    uploadWrapper : `upload_wrapper.temporaryUploadedFileWrapper`
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
    def __init__(self, uploadWrapper, *args, **kwargs):
        self._upload = uploadWrapper

    def __init_subclass__(cls, **kwargs):
        # Registers subclasses of this class with set `name` class parameters
        # as availible translators
        name = getattr(cls, "name", False)
        if name and name is not None:
            super().__init_subclass__(**kwargs)
            UploadProcessor.processors[cls.name] = cls

    @classmethod
    @abstractmethod
    def canProcess(self, upload):
        """Returns ``True`` when the processor knows how to process the given
        upload (file) type.

        Parameters
        ----------
        upload : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.

        Returns
        -------
        canProcess : `bool`
            `True` when the processor knows how to handle uploaded file and
            `False` otherwise
        """
        raise NotImplemented()

    @classmethod
    def getProcessor(cls, upload):
        """Get the processor class that can handle given upload. If multiple
        processors declare the ability to process the given upload the
        processor with highest prirority is selected.

        Parameters
        ----------
        upload : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.

        Returns
        -------
        processor : `cls`
            Processor class that can process the given upload.`

        Raises
        ------
        ValueError
            None of the registered processors can process the  upload.
        """
        processors = []
        for processor in cls.processors.values():
            if processor.canProcess(upload):
                processors.append(processor)
        processors.sort(key=lambda processor: processor.priority, reverse=True)

        if processors:
            if len(processors) > 1:
                # I think this should never be an issue really, but just in case
                names = [proc.name for proc in processors]
                warnings.warn("Multiple processors declared ability to process "
                              f"the given upload: {names}. \n Using {names[-1]} "
                              "to process FITS.")
            return processors[0]
        else:
            raise ValueError("None of the known processors can handle this upload.\n "
                             f"Known processors: {list(cls.processors.keys())}")

    @classmethod
    def fromUpload(cls, upload):
        """Return an instantiated Processor that can process the upload.

        Parameters
        ----------
        upload : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.

        Returns
        -------
        processor : `object`
            Instance of a Processor class that can process the given upload

        Raises
        ------
        ValueError
            None of the registered processors can process the  upload.
        """
        processorCls = cls.getProcessor(upload)
        return processorCls(upload)

    def process(self):#, upload):
        """Process the given upload.

        Parameters
        ----------
        upload : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.
        """
        # TODO: get some error handling here
        self.storeHeaders()
        #self.detect_trails()
        self.storeThumbnails()

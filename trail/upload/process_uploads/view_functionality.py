"""Functions invoked by views."""


from .upload_wrapper import TemporaryUploadedFileWrapper
from .upload_processor import UploadProcessor


__all__ = ["process_upload", ]


def process_uploads(uploads):
    """Given a uploaded file, normalizes and inserts header data into the DB,
    creates and stores small and large thumbnails and saves a copy of the
    uploaded file.

    Parameters
    ----------
    img : `django.core.files.uploadedfile.TemporaryUploadedFile`
        Uploaded fits image
    """
    for upload in uploads:
        uploadWrapper = TemporaryUploadedFileWrapper(upload)
        uploadProcessor = UploadProcessor.fromUpload(uploadWrapper)
        uploadProcessor.process()
        uploadWrapper.save()

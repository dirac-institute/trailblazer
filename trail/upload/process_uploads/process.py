"""Functions invoked by views."""


from .tmpfile import TemporaryUploadedFileWrapper
from upload.process_uploads.upload_processor import UploadProcessor


__all__ = ["process_upload", ]


def process_upload(img):
    """Given a uploaded file, normalizes and inserts header data into the DB,
    creates and stores small and large thumbnails and saves a copy of the
    uploaded file.

    Parameters
    ----------
    img : `django.core.files.uploadedfile.TemporaryUploadedFile`
        Uploaded fits image
    """
    upload = TemporaryUploadedFileWrapper(img)
    uploadProcessor = UploadProcessor.fromUpload(upload)
    uploadProcessor.process()
    upload.save()

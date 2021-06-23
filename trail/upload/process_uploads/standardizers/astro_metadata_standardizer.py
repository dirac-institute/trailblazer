"""
Class that interfaces astro_metadata_translator module to standardize header
metadata.
"""


from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata

from astro_metadata_translator import MetadataTranslator, ObservationInfo


__all__ = ["AstroMetadataTranslator", ]


class AstroMetadataTranslator(HeaderStandardizer):

    name = "astro_metadata_translator"
    priority = 2

    def __init__(self, header, filename=None, **kwargs):
        super().__init__(header, **kwargs)
        self.filename = filename
        self.obsInfo = ObservationInfo(header, filename=filename)

    @classmethod
    def canStandardize(cls, header, filename=None, **kwargs):
        try:
            ObservationInfo(header, filename=filename)
        except ValueError:
            return False
        else:
            return True

    def standardizeMetadata(self):
        location = self.obsInfo.location
        meta = Metadata(
            obs_lon=location.lon.value,
            obs_lat=location.lat.value,
            obs_height=location.height.value,
            datetime_begin=self.obsInfo.datetime_begin.tt.datetime.isoformat(),
            datetime_end=self.obsInfo.datetime_end.tt.datetime.isoformat(),
            standardizer_name=f"{self.name}.{self.obsInfo._translator.name}",
            telescope=self.obsInfo.telescope,
            instrument=self.obsInfo.instrument,
            science_program=self.obsInfo.science_program,
            exposure_duration=self.obsInfo.exposure_time.value,
            filter=self.obsInfo.physical_filter
        )
        return meta

"""
Class that interfaces astro_metadata_translator module to standardize header
metadata. 
"""


from upload.process_uploads.header_standardizer import HeaderStandardizer

from astro_metadata_translator import MetadataTranslator, ObservationInfo


__all__ = ["AstroMetadataTranslator", ]


class AstroMetadataTranslator(HeaderStandardizer):

    name = "astro_metadata_translator"

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
        standardizedKeys = {}

        location = self.obsInfo.location
        standardizedKeys["obs_lon"] = location.lon.value
        standardizedKeys["obs_lat"] = location.lat.value
        standardizedKeys["obs_height"] = location.height.value

        # translator names are easy everyday names
        # the rest I don't know how they'll vary over different
        # instruments but I can assume potentially by a lot?
        standardizedKeys["metadata_translator_name"] = self.obsInfo._translator.name
        standardizedKeys["telescope"] = self.obsInfo.telescope
        standardizedKeys["instrument"] = self.obsInfo.instrument
        standardizedKeys["science_program"] = self.obsInfo.science_program

        # TODO: see Las Cumbres and then come back and fix!
        standardizedKeys["datetime_begin"] = self.obsInfo.datetime_begin.tt.datetime.isoformat()
        standardizedKeys["datetime_end"] = self.obsInfo.datetime_end.tt.datetime.isoformat()
        standardizedKeys["exposure_duration"] = self.obsInfo.exposure_time.value

        standardizedKeys["physical_filter"] = self.obsInfo.physical_filter


        return standardizedKeys

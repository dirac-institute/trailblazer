from astropy.time import Time
from astropy.io import fits
from astropy.wcs import WCS

wcs_input_dict = {
    'CTYPE1': 'RA---TAN',
    'CUNIT1': 'deg',
    'CDELT1': -0.0002777777778,
    'CRPIX1': 1,
    'CRVAL1': 337.5202808,
    'NAXIS1': 1024,
    'CTYPE2': 'DEC--TAN',
    'CUNIT2': 'deg',
    'CDELT2': 0.0002777777778,
    'CRPIX2': 1,
    'CRVAL2': -20.833333059999998,
    'NAXIS2': 1024
}
wcs_helix_dict = WCS(wcs_input_dict)


# >>> testgrounds.wcs_helix_dict
# WCS Keywords
#
# Number of WCS axes: 2
# CTYPE : 'RA---TAN'  'DEC--TAN'
# CRVAL : 337.5202808  -20.83333306
# CRPIX : 1.0  1.0
# PC1_1 PC1_2  : 1.0  0.0
# PC2_1 PC2_2  : 0.0  1.0
# CDELT : -0.0002777777778  0.0002777777778
# NAXIS : 1024  1024
#
# >>> wcs.wcs.cdelt
# array([1., 1.])



# but for an older SDSS WCS the cdelt is a suspect
# >>> wcs
# WCS Keywords
#
# Number of WCS axes: 2
# CTYPE : 'RA---TAN'  'DEC--TAN'
# CRVAL : 1.66637505529  -0.523564161773
# CRPIX : 1025.0  745.0
# CD1_1 CD1_2  : -5.91913039931e-09  0.000109955134258
# CD2_1 CD2_2  : 0.000109985222679  -6.9465606613e-10
# NAXIS : 2048  1489
#
# >>> wcs.wcs.cdelt
# array([1., 1.])

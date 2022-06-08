import numpy

def getXYZFromWcs(self, ra, dec):
    """Convert ra and dec into xyz coordinates.
    """
    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    return {"x": x, "y": y, "z": z}

def isWcsQueryParamMissing(self, queryParams):
    """Check if the sky boundary is correctly specified."""
    return not (self.RALOW in queryParams and self.RAHIGH in queryParams
                and self.DECHIGH in queryParams and self.DECLOW in queryParams)

import os
import shutil
import tempfile

import yaml

from django.test import TestCase

from upload.process_uploads.tmpfile import TemporaryUploadedFileWrapper
from upload.process_uploads import processors


TESTDIR = os.path.abspath(os.path.dirname(__file__))


class MockTmpUploadedFile:
    def __init__(self, fname, sourcePath=""):
        self.name = fname
        self._sourcePath = sourcePath
        self.sourceFilePath = os.path.join(sourcePath, fname)

    def read(self):
        with open(self.sourceFilePath, "rb") as f:
            return f.read()

    def temporary_file_path(self):
        return self.sourceFilePath


class TemporaryUploadedFileWrapperTestCase(TestCase):
    """Tests the TemporaryUploadedFileWrapper functionality. """
    testDataDir = os.path.join(TESTDIR, "data")

    def setUp(self):
        self.tmpTestDir = tempfile.mkdtemp(dir=TESTDIR)
        TemporaryUploadedFileWrapper.save_root = self.tmpTestDir

        self.testData = {
            # filename: (basename, ext)
            "reduced_A3671-C2018_F4-R-3.fit": ("reduced_A3671-C2018_F4-R-3", ".fit"),
            "reduced_bi327715.fits": ("reduced_bi327715", ".fits"),
            "reduced_c4d_200306_000415_ori.fits.fz": ("reduced_c4d_200306_000415_ori", ".fits.fz"),
            "reduced_calexp-0941420_23.fits": ("reduced_calexp-0941420_23", ".fits"),
            "reduced_HSCA21787010.fits": ("reduced_HSCA21787010", ".fits"),
            "reduced_frame-i-008108-5-0025.fits": ("reduced_frame-i-008108-5-0025", ".fits"),
        }

        self.fits = []
        for fname in self.testData.keys():
            tmp = MockTmpUploadedFile(fname, self.testDataDir)
            self.fits.append(TemporaryUploadedFileWrapper(tmp))

    def tearDown(self):
        if os.path.exists(self.tmpTestDir):
            shutil.rmtree(self.tmpTestDir, ignore_errors=True)

    def testBasename(self):
        """Verify extracted file name without extensions is the same as
        expected solution.
        """
        for fits, (fname, expected) in zip(self.fits, self.testData.items()):
            with self.subTest(filename=fname + " basename"):
                self.assertEqual(fits.basename, expected[0])

    def testExtension(self):
        """Verify extracted extensions behave as expected solutions."""
        for fits, (fname, expected) in zip(self.fits, self.testData.items()):
            with self.subTest(filename=fname + " extension"):
                self.assertEqual(fits.extension, expected[1])

    def testSave(self):
        """Verify saving a file works as expected."""
        # TODO: silly for now untill I get boto3 uploading working, here as
        # a placeholder. Note we set up the save directory in the test setup
        fits = self.fits[0]
        tgtPath = fits.save()

        expected = os.path.join(self.tmpTestDir, fits.filename)
        self.assertEqual(tgtPath, expected)
        self.assertTrue(os.path.exists(tgtPath))


class FitsProcessorTestCase(TestCase):
    """Tests the internal logic of FitsProcessor."""
    testDataDir = os.path.join(TESTDIR, "data")

    def setUp(self):
        self.tmpTestDir = tempfile.mkdtemp(dir=TESTDIR)
        TemporaryUploadedFileWrapper.save_root = self.tmpTestDir
        processors.UploadProcessor.media_root = self.tmpTestDir

        fnames = os.listdir(self.testDataDir)
        self.fits = []
        for fname in fnames:
            if "fits" in fname or "fit" in fname:
                tmp = MockTmpUploadedFile(fname, self.testDataDir)
                self.fits.append(TemporaryUploadedFileWrapper(tmp))

        with open(os.path.join(self.testDataDir, "expectedStandardizedValues.yaml")) as f:
            self.standardizedAnswers = yaml.safe_load(f)

    def tearDown(self):
        if os.path.exists(self.tmpTestDir):
            shutil.rmtree(self.tmpTestDir)

    def testFileRecognition(self):
        """Test FitsProcessor correctly recognizes files it can process."""
        for fits in self.fits:
            with self.subTest(filename=fits.filename):
                self.assertTrue(processors.FitsProcessor.canProcess(fits))

    def testStandardize(self):
        """Tests whether WCS and Header Metadata are standardized as expected."""
        for fits in self.fits:
            fitsProcessor = processors.FitsProcessor(fits)
            expected = self.standardizedAnswers[fits.filename]

            # TODO: make all fits pass both tests. Live with this crutch for now
            # TODO: Do the math how much cartesian unit circle coordinates distance
            # move on the sky and then fix the number of test decimals to something
            # reasonable.
            if expected["wcs"]:
                expectedWcs = expected["wcs"]
                with self.subTest(fitsname=fits.filename + " WCS"):
                    try:
                        producedWcs = fitsProcessor.standardizedWcs()
                    except Exception as exc:
                        self.fail(exc)

                    # test expected keys are present. testStoreHeader will test
                    # whether this indeed matches the DB schema later...
                    self.assertEqual(expectedWcs.keys(), producedWcs.keys())

                    # test produced results are actully correct
                    for key in expectedWcs:
                        self.assertAlmostEqual(expectedWcs[key], producedWcs[key], 3)


            if expected["header"]:
                expectedHeader = expected["header"]
                with self.subTest(fitsname=fits.filename + " HEADER"):
                    try:
                        producedHeader = fitsProcessor.standardizedHeaderMetadata()
                    except Exception as exc:
                        self.fail(exc)
                        
                    self.assertEqual(expectedHeader.keys(), producedHeader.keys())

                    approximatelyEqualKeys = ("obs_lon", "obs_lat", "obs_height")
                    for key in approximatelyEqualKeys:
                        self.assertAlmostEqual(expectedHeader[key], producedHeader[key], 5)

                    for key in expectedHeader:
                        if key in approximatelyEqualKeys:
                            self.assertAlmostEqual(expectedHeader[key], producedHeader[key], 5)
                        else:
                            self.assertEqual(expectedHeader[key], producedHeader[key])

    def testStoreHeader(self):
        """Tests whether store header executes on an SDSS frame; this verifies
        the created standardized dictionary has correcly named keys.
        """
        data = MockTmpUploadedFile("reduced_frame-i-008108-5-0025.fits",
                                   self.testDataDir)
        fits = TemporaryUploadedFileWrapper(data)
        fitsProcessor = processors.FitsProcessor(fits)
        try:
            fitsProcessor.storeHeader()
        except Exception as exc:
            self.fail(exc)

    def testStoreThumbnails(self):
        """Tests whether two thumbnails appear at the expected location."""
        data = MockTmpUploadedFile("reduced_frame-i-008108-5-0025.fits",
                                   self.testDataDir)
        fits = TemporaryUploadedFileWrapper(data)
        fitsProcessor = processors.FitsProcessor(fits)

        try:
            fitsProcessor.storeThumbnails()
        except Exception as exc:
            self.fail(exc)

        large = os.path.join(self.tmpTestDir, fits.basename+'_large.png')
        small = os.path.join(self.tmpTestDir, fits.basename+'_small.png')
        self.assertTrue(os.path.exists(large))
        self.assertTrue(os.path.exists(small))


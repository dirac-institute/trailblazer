import os
import shutil
import tempfile

import yaml

from django.test import TestCase

from upload.models import StandardizedHeader, Thumbnails
from upload.process_uploads.upload_wrapper import TemporaryUploadedFileWrapper
from upload.process_uploads.upload_processor import UploadProcessor
from upload.process_uploads.fits_processor import FitsProcessor
import upload.process_uploads.header_standardizer as header_standardizer


TESTDIR = os.path.abspath(os.path.dirname(__file__))


class MockAstrometryServer:
    def __init__(self):
        pass

    def solve_from_image(self, path_to_file, preprocess=True, solve_timeout=120):
        path = path_to_file.rsplit(".", 1)[0] + ".txt"
        try:
            return open(path).read()
        except FileNotFoundError:
            return {}


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
            "cutout_A3671-C2018_F4-R-3.fit": ("cutout_A3671-C2018_F4-R-3", ".fit"),
            "cutout_bi327715.fits": ("cutout_bi327715", ".fits"),
            "cutout_c4d_200306_000415_ori.fits.fz": ("cutout_c4d_200306_000415_ori", ".fits.fz"),
            "cutout_calexp-0941420_23.fits": ("cutout_calexp-0941420_23", ".fits"),
            "cutout_HSCA21787010.fits": ("cutout_HSCA21787010", ".fits"),
            "cutout_frame-i-008108-5-0025.fits": ("cutout_frame-i-008108-5-0025", ".fits"),
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


class UploadProcessorTestCase(TestCase):
    """Tests the internal logic of FitsProcessor."""
    testDataDir = os.path.join(TESTDIR, "data")

    def setUp(self):
        self.tmpTestDir = tempfile.mkdtemp(dir=TESTDIR)
        TemporaryUploadedFileWrapper.save_root = self.tmpTestDir
        Thumbnails.SMALL_THUMB_ROOT = self.tmpTestDir
        Thumbnails.LARGE_THUMB_ROOT = self.tmpTestDir

        header_standardizer.ASTROMETRY_KEY = "test"
        header_standardizer.ASTRONET_CLIENT = MockAstrometryServer()

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
                self.assertTrue(FitsProcessor.canProcess(fits))

    def testProcessorMatch(self):
        """Tests whether the correct processors are matched to correct files."""
        for fits in self.fits:
            expected = self.standardizedAnswers[fits.filename]
            fitsProcessor = UploadProcessor.fromFileWrapper(fits)
            with self.subTest(fitsname=fits.filename):
                self.assertEqual(fitsProcessor.name, expected["metadata"]["processor_name"])

    def testStandardize(self):
        """Tests whether WCS and Header Metadata are standardized as expected."""
        for fits in self.fits:
            data = self.standardizedAnswers[fits.filename]
            # TODO: Do the math how much cartesian unit circle coordinates move
            # on the sky and then fix the isClose test to something reasonable
            if not data["runProcessing"]:
                continue

            with self.subTest(fitsname=fits.filename + " INSTANTIATION"):
                fitsProcessor = UploadProcessor.fromFileWrapper(fits)

            with self.subTest(fitsname=fits.filename + " PROCESSING"):
                produced = fitsProcessor.standardizeHeader()

            expected = StandardizedHeader.fromDict(data)

            with self.subTest(fitsname=fits.filename + " STANDARDIZE"):
                self.assertEqual(produced, expected)

    def testStoreHeaders(self):
        """Tests whether store header executes on an SDSS frame; this verifies
        the created standardized dictionary has correcly named keys.
        """
        data = MockTmpUploadedFile("cutout_frame-i-008108-5-0025.fits",
                                   self.testDataDir)
        fits = TemporaryUploadedFileWrapper(data)
        fitsProcessor = UploadProcessor.fromFileWrapper(fits)
        fitsProcessor.standardizeHeader()

    def testStoreThumbnails(self):
        """Tests whether two thumbnails appear at the expected location."""
        data = MockTmpUploadedFile("cutout_frame-i-008108-5-0025.fits",
                                   self.testDataDir)
        fits = TemporaryUploadedFileWrapper(data)
        fitsProcessor = UploadProcessor.fromFileWrapper(fits)
        fitsProcessor.createThumbnails()

        large = os.path.join(self.tmpTestDir, fits.basename+'_large.jpg')
        small = os.path.join(self.tmpTestDir, fits.basename+'_small.jpg')
        self.assertTrue(os.path.exists(large))
        self.assertTrue(os.path.exists(small))

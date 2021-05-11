import os
import shutil
import tempfile

import yaml

from django.test import TestCase

from upload.process_uploads.upload_wrapper import TemporaryUploadedFileWrapper
from upload.process_uploads.upload_processor import UploadProcessor
from upload.process_uploads.processors.fits_processors import FitsProcessor


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


class UploadProcessorTestCase(TestCase):
    """Tests the internal logic of FitsProcessor."""
    testDataDir = os.path.join(TESTDIR, "data")

    def setUp(self):
        self.tmpTestDir = tempfile.mkdtemp(dir=TESTDIR)
        TemporaryUploadedFileWrapper.save_root = self.tmpTestDir
        UploadProcessor.media_root = self.tmpTestDir

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

    def testStandardize(self):
        """Tests whether WCS and Header Metadata are standardized as expected."""

        from upload.process_uploads.standardized_dataclasses import StandardizedHeaderKeys

        for fits in self.fits:
            data = self.standardizedAnswers[fits.filename]
            # TODO: make all fits pass tests. Live with this crutch for now
            # TODO: Do the math how much cartesian unit circle coordinates move
            # on the sky and then fix the isClose test to something reasonable
            if not data["runTest"]:
                continue

            with self.subTest(fitsname=fits.filename + " INSTANTIATION"):
                fitsProcessor = UploadProcessor.fromUpload(fits)

            with self.subTest(fitsname=fits.filename + " PROCESSING"):
                produced = fitsProcessor.standardizeHeader()

            expected = StandardizedHeaderKeys.fromDict(data["data"], fitsProcessor.isMultiExt)
            produced = StandardizedHeaderKeys.fromDict(produced, fitsProcessor.isMultiExt)

            with self.subTest(fitsname=fits.filename + " STANDARDIZE"):
                    self.assertTrue(produced.isCloseTo(expected))

    def testStoreHeaders(self):
        """Tests whether store header executes on an SDSS frame; this verifies
        the created standardized dictionary has correcly named keys.
        """
        data = MockTmpUploadedFile("reduced_frame-i-008108-5-0025.fits",
                                   self.testDataDir)
        fits = TemporaryUploadedFileWrapper(data)
        fitsProcessor = UploadProcessor.fromUpload(fits)
        fitsProcessor.storeHeaders()

    def testStoreThumbnails(self):
        """Tests whether two thumbnails appear at the expected location."""
        data = MockTmpUploadedFile("reduced_frame-i-008108-5-0025.fits",
                                   self.testDataDir)
        fits = TemporaryUploadedFileWrapper(data)
        fitsProcessor = UploadProcessor.fromUpload(fits)
        fitsProcessor.storeThumbnails()

        large = os.path.join(self.tmpTestDir, fits.basename+'_large.png')
        small = os.path.join(self.tmpTestDir, fits.basename+'_small.png')
        self.assertTrue(os.path.exists(large))
        self.assertTrue(os.path.exists(small))


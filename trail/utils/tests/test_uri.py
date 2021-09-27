import os.path
import posixpath

from django.test import TestCase
from utils.uri import os2posix, posix2os, URI


class URITestCase(TestCase):
    """Tests for URI.
    """

    def testUri(self):
        """Tests whether URI instantiates correctly given different
        arguments.
        """
        # Root to use for relative paths
        testRoot = "/tmp/"

        # uriStrings is a list of tuples containing test string, forceAbsolute,
        # forceDirectory as arguments to URI and scheme, netloc and path
        # as expected attributes. Test asserts constructed equals to expected.
        # 1) no determinable schemes (ensures schema and netloc are not set)
        osRelFilePath = os.path.join(testRoot, "relative/file.ext")
        uriStrings = [
            ("relative/file.ext", True, False, "", "", osRelFilePath),
            ("relative/file.ext", False, False, "", "", "relative/file.ext"),
            ("test/../relative/file.ext", True, False, "", "", osRelFilePath),
            ("test/../relative/file.ext", False, False, "", "", "relative/file.ext"),
            ("relative/dir", False, True, "", "", "relative/dir/")
        ]
        # 2) implicit file scheme, tests absolute file and directory paths
        uriStrings.extend((
            ("/rootDir/absolute/file.ext", True, False, "file", "", '/rootDir/absolute/file.ext'),
            ("~/relative/file.ext", True, False, "file", "", os.path.expanduser("~/relative/file.ext")),
            ("~/relative/file.ext", False, False, "file", "", os.path.expanduser("~/relative/file.ext")),
            ("/rootDir/absolute/", True, False, "file", "", "/rootDir/absolute/"),
            ("/rootDir/absolute", True, True, "file", "", "/rootDir/absolute/"),
            ("~/rootDir/absolute", True, True, "file", "", os.path.expanduser("~/rootDir/absolute/"))
        ))
        # 3) explicit file scheme, absolute and relative file and directory URI
        posixRelFilePath = posixpath.join(testRoot, "relative/file.ext")
        uriStrings.extend((
            ("file:///rootDir/absolute/file.ext", True, False, "file", "", "/rootDir/absolute/file.ext"),
            ("file:relative/file.ext", True, False, "file", "", posixRelFilePath),
            ("file:///absolute/directory/", True, False, "file", "", "/absolute/directory/"),
            ("file:///absolute/directory", True, True, "file", "", "/absolute/directory/")
        ))
        # 4) S3 scheme (ensured Keys as dirs and fully specified URIs work)
        uriStrings.extend((
            ("s3://bucketname/rootDir/", True, False, "s3", "bucketname", "/rootDir/"),
            ("s3://bucketname/rootDir", True, True, "s3", "bucketname", "/rootDir/"),
            ("s3://bucketname/rootDir/relative/file.ext", True, False, "s3",
             "bucketname", "/rootDir/relative/file.ext")
        ))

        for uriInfo in uriStrings:
            uri = URI(uriInfo[0], root=testRoot, forceAbsolute=uriInfo[1],
                            forceDirectory=uriInfo[2])
            with self.subTest(uri=uriInfo[0]):
                self.assertEqual(uri.scheme, uriInfo[3], "test scheme")
                self.assertEqual(uri.netloc, uriInfo[4], "test netloc")
                self.assertEqual(uri.path, uriInfo[5], "test path")

        # test root becomes abspath(".") when not specified, note specific
        # file:// scheme case
        uriStrings = (
            ("file://relative/file.ext", True, False, "file", "relative", "/file.ext"),
            ("file:relative/file.ext", False, False, "file", "", os.path.abspath("relative/file.ext")),
            ("file:relative/dir/", True, True, "file", "", os.path.abspath("relative/dir")+"/"),
            ("relative/file.ext", True, False, "", "", os.path.abspath("relative/file.ext"))
        )

        for uriInfo in uriStrings:
            uri = URI(uriInfo[0], forceAbsolute=uriInfo[1], forceDirectory=uriInfo[2])
            with self.subTest(uri=uriInfo[0]):
                self.assertEqual(uri.scheme, uriInfo[3], "test scheme")
                self.assertEqual(uri.netloc, uriInfo[4], "test netloc")
                self.assertEqual(uri.path, uriInfo[5], "test path")

        # File replacement
        uriStrings = (
            ("relative/file.ext", "newfile.fits", "relative/newfile.fits"),
            ("relative/", "newfile.fits", "relative/newfile.fits"),
            ("https://www.trailblazer.org/configs/", "config.yaml", "/configs/config.yaml"),
            ("s3://bucketname/directory/", "config.yaml", "/directory/config.yaml"),
            ("s3://bucketname/directory/myconfig.yaml", "config.yaml", "/directory/config.yaml")
        )

        for uriInfo in uriStrings:
            uri = URI(uriInfo[0], forceAbsolute=False)
            uri.updateFile(uriInfo[1])
            with self.subTest(uri=uriInfo[0]):
                self.assertEqual(uri.path, uriInfo[2])

        # Copy constructor
        uri = URI("s3://bucketname/directory", forceDirectory=True)
        uri2 = URI(uri)
        self.assertEqual(uri, uri2)
        uri = URI("file://bucketname/directory/file.txt")
        uri2 = URI(uri)
        self.assertEqual(uri, uri2)

    def testPosix2OS(self):
        """Test round tripping of the posix to os.path conversion helpers."""
        testPaths = ("/a/b/c.e", "a/b", "a/b/", "/a/b", "/a/b/", "a/b/c.e")
        for p in testPaths:
            with self.subTest(path=p):
                self.assertEqual(os2posix(posix2os(p)), p)

    def testSplit(self):
        """Tests split functionality."""
        testRoot = "/tmp/"

        testPaths = ("/absolute/file.ext", "/absolute/",
                     "file:///absolute/file.ext", "file:///absolute/",
                     "s3://bucket/root/file.ext", "s3://bucket/root/",
                     "relative/file.ext", "relative/")

        osRelExpected = os.path.join(testRoot, "relative")
        expected = (("file:///absolute/", "file.ext"), ("file:///absolute/", ""),
                    ("file:///absolute/", "file.ext"), ("file:///absolute/", ""),
                    ("s3://bucket/root/", "file.ext"), ("s3://bucket/root/", ""),
                    (f"file://{osRelExpected}/", "file.ext"), (f"file://{osRelExpected}/", ""))

        for p, e in zip(testPaths, expected):
            with self.subTest(path=p):
                uri = URI(p, testRoot)
                head, tail = uri.split()
                self.assertEqual((head.geturl(), tail), e)

        # explicit file scheme should force posixpath, check os.path is ignored
        posixRelFilePath = posixpath.join(testRoot, "relative")
        uri = URI("file:relative/file.ext", testRoot)
        head, tail = uri.split()
        self.assertEqual((head.geturl(), tail), (f"file://{posixRelFilePath}/", "file.ext"))

        # check head can be empty
        curDir = os.path.abspath(os.path.curdir) + os.sep
        uri = URI("file.ext", forceAbsolute=False)
        head, tail = uri.split()
        self.assertEqual((head.geturl(), tail), (curDir, "file.ext"))

        # ensure empty path is not a problem and conforms to os.path.split
        uri = URI("", forceAbsolute=False)
        head, tail = uri.split()
        self.assertEqual((head.geturl(), tail), (curDir, ""))

        uri = URI(".", forceAbsolute=False)
        head, tail = uri.split()
        self.assertEqual((head.geturl(), tail), (curDir, "."))

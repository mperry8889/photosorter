#!/usr/bin/env python

from photosorter import PhotoSorter
from photosorter import Photo
from photosorter import Bucket
from photosorter import SORT_BUCKETS

import unittest

class TestPhoto(unittest.TestCase):
   pass

class TestBucket(unittest.TestCase):
   pass

class TestPhotoSorter(unittest.TestCase):

   def test_loadBuckets(self):
      """Test that buckets are loaded properly"""
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      self.assertEquals(sorted(map(lambda i: i.name, p.buckets)), sorted(SORT_BUCKETS))

   def test_checkForFiles(self):
      """Check that files are in the file list"""
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      self.assertNotEquals(len(p.filelist), 0)
      self.assertNotEquals(len(p.photolist), 0)
      self.assertEquals(len(p.filelist), len(p.photolist))

   def test_transforms(self):
      """Flip horizontally and rotate all images 5 times (90, 180, 270, 360, 540) degrees.  
      All images should end up rotated a true 90 degrees and flipped horizontally."""
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      for f in p.photolist:
         for i in range(0, 5):
            p.rotate_clockwise(f, updateGui=False)
            p.flip_horizontal(f, updateGui=False)
         self.assertEquals(f.rotation, 90)
         self.assertEquals(f.flip_horizontal, True)

   def test_bucketGenerator(self):
      """Iterate through the list of buckets, in sort-worthy order"""
      class C(object):
         def __init__(self, name):
            self.name = "%s" % name

      buckets = []
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      for i in p.next_bucket():
         buckets.append(i)

      self.assertEquals(sorted([i.name for i in buckets]), [i.name for i in p.buckets])

   def test_photoGenerator(self):
      """Iterate through list of photos in current bucket"""
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)

      photos = [1, 2, 3, 4, 5]
      generated_photos = []

      # just do one bucket iteration
      for b in p.next_bucket():
         p.CURRENT_BUCKET.unsorted = photos
         for i in p.next_photo():
            generated_photos.append(i)
         break

      self.assertEquals(photos, generated_photos)

   def test_primeUnsortedList(self):
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      i = 0
      for b in p.next_bucket():
         if i == 0:
            self.assertEquals(b.unsorted, p.filelist)
            i += 1
         else:
            self.assertEquals(b.unsorted, [])



if __name__ == "__main__":
   unittest.main()



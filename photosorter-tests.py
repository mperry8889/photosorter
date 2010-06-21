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

   def test_multiBucketPhotoGenerator(self):
      """Iterate through list of potos in multiple buckets"""
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      p.buckets = [Bucket(i) for i in range(0, 5)]
      photos = [0, 1, 2, 3, 4]
      generated_photos = []
      for i in range(0, 5):
         p.buckets[i].unsorted.add(photos[i])

      for b in p.next_bucket():
         for photo in p.next_photo():
            generated_photos.append(photo)

      self.assertEquals(sorted(generated_photos), sorted(photos))

   def test_primeUnsortedList(self):
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      i = 0
      for b in p.next_bucket():
         if i == 0:
            self.assertEquals(b.unsorted, set(p.filelist))
            i += 1
         else:
            self.assertEquals(b.unsorted, set())


   def test_basicSortDirections(self):
      """Check basic sort directions"""
      
      def direction():
         values = [-1, 0, 1, -1, 0, 1]
         for i in values:
            yield i

      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      p.buckets = [Bucket(i) for i in [1, 2, 3]]
      photos = [1, 2, 3]
      
      for b in p.next_bucket():
         b.unsorted = photos
         break

      for b in p.next_bucket():
         d = direction()
         for photo in p.next_photo():
            p.sort_photo(photo, b, d.next())
         
         self.assertEquals(len(b.unsorted), 0)
         self.assertEquals(len(b.before), 1)
         self.assertEquals(len(b.after), 1)
         self.assertEquals(len(b.unknown), 1)
         break

   def test_invalidSortDirection(self):
      """Invalid sort direction"""
      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      p.buckets = [Bucket(i) for i in [1,2,3]]
      photos = [1, 2, 3]
      for b in p.next_bucket():
         b.unsorted = photos
         break

      for b in p.next_bucket():
         for photo in p.next_photo():
            self.assertRaises(ValueError, p.sort_photo, photo, b, -2)
            self.assertRaises(ValueError, p.sort_photo, photo, b, 2)
            self.assertRaises(ValueError, p.sort_photo, photo, b, "abcd")
            self.assertRaises(ValueError, p.sort_photo, photo, b, None)

   def test_simpleReconcileBuckets(self):
      """Simple case of sorting and reconciling buckets.  3 items, 3 buckets: 1 unknown as of bucket 2, 1 before bucket 2, 1 after bucket 2"""
      def direction():
         values = [-1, 0, 1, -1, 0, 1]
         for i in values:
            yield i

      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      p.buckets = [Bucket(i) for i in [1, 2, 3]]
      photos = [1, 2, 3]
      
      for b in p.next_bucket():
         b.unsorted = set(photos)
         break

      for b in p.next_bucket():
         d = direction()
         for photo in p.next_photo():
            p.sort_photo(photo, b, d.next())
         
         self.assertEquals(len(b.unsorted), 0)
         self.assertEquals(len(b.before), 1)
         self.assertEquals(len(b.after), 1)
         self.assertEquals(len(b.unknown), 1)
         break

      self.assertEquals(p.buckets[1].before, p.buckets[0].unsorted)
      self.assertEquals(p.buckets[1].after, p.buckets[2].unsorted)
      self.assertEquals(p.buckets[1].unknown, set([2]))

   def test_mediumReconcileBuckets(self):
      """More advanced case of reconciling several buckets"""
      def direction():
         values = [-1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1]
         for i in values:
            yield i

      def photosByBucket(p, bucket):
         retv = []
         for i in p:
            if p[i] == bucket:
               retv.append(i)
         return retv

      p = PhotoSorter(loadFromDisk=False, dumpToDisk=False)
      p.buckets = [Bucket(i) for i in [1, 2, 3, 4]]
      photos = {
      #  photo number: bucket
         1:            3,
         2:            2,
         3:            4,
         4:            2,
         5:            1,
         6:            4,
         7:            1,
         8:            4,
         9:            4,
      }
      
      for b in p.next_bucket():
         b.unsorted = set(photos)
         break

      for b in p.next_bucket():
         for photo in p.next_photo():
            if photos[photo] >= int(b.name):
               p.sort_photo(photo, b, 1)
            elif photos[photo] < int(b.name):
               p.sort_photo(photo, b, -1)
            else:
               p.sort_photo(photo, b, 0)
      
      for b in p.next_bucket():
         self.assertEquals(sorted(list(b.during)), sorted(photosByBucket(photos, int(b.name))))



if __name__ == "__main__":
   unittest.main()



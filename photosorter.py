#!/usr/bin/env python
#-*- coding: iso-8859-15 -*-


import os
import pygtk
pygtk.require('2.0')
import gtk
import pango
from PIL import Image as PILImage
import pickle
from copy import copy


SORT_BUCKETS = [1950, 1960, 1970, 1980, 1990, 2000]

class Photo(object):
   def __init__(self, filename, bucket=None):
      self.bucket = bucket
      self.fully_sorted = False  # fully sorted when compared against
                                 # 2 adjacent buckets; e.g. greater than
                                 # 1980 and less than 1990, or less than
                                 # 1960 but there are no lesser buckets
                                 # to sort into.

      self.filename = filename
      self.rotation = 0
      self.flip_horizontal = False


class Bucket(object):
   def __init__(self, name):
      self.name = name

      # a photo can be in one of 5 states relative to a bucket:
      # 1. before the bucket. e.g. photo was taken in 1962, bucket is 1980 
      # 2. after the bucket. e.g., photo was taken in 2007, bucket is 1970
      # 3. during the bucket. e.g., photo was taken in 1997, bucket is 1990
      # 4. unsorted. photo has not been displayed for sorting yet
      # 5. unknown. photo was displayed but relative date is unknown
      
      self.before = set()
      self.after = set()
      self.during = set()
      self.unsorted = set()
      self.unknown = set()

      self.fully_sorted = False

   def __gt__(self, rhs):
      return int(self.name) > int(rhs.name)
   def __lt__(self, rhs):
      return not self.__gt__(rhs)




class PhotoSorter(object):
   def __init__(self, gui=None, loadFromDisk=True, dumpToDisk=True):
      self.gui = gui
      self.loadFromDisk = loadFromDisk
      self.dumpToDisk = dumpToDisk

      self.CURRENT_PHOTO = None
      self.CURRENT_BUCKET = None

      # get of files to sort through and create objects 
      self.filelist = os.listdir("images/")
      filter = lambda f: f.upper().endswith(".JPG")
      for file in self.filelist:
         if not filter(file):
            self.filelist.remove(file)
      self.photolist = [Photo(f) for f in self.filelist]

      if self.loadFromDisk:
         # resume sorting from point of last exit
         self.buckets = [self.unpickle("bucket-%s" % b, Bucket, "%s" % b) for b in SORT_BUCKETS]
         
         self.CURRENT_PHOTO = self.unpickle("current_photo", None, newObject=False)
         self.CURRENT_BUCKET = self.unpickle("current_bucket", None, newObject=False)
      
      # used mostly in testing
      else:
         self.buckets = [Bucket(b) for b in SORT_BUCKETS]
         
         self.CURRENT_PHOTO = None
         self.CURRENT_BUCKET = None
 
      # bail in there case where only one of current bucket or photo is serialized but
      # not the other; don't do any recovery, just begin menual intervention here.
      # that shouldn't happen and it's not worth figuring out what to do there for 
      # this one-time use app.
      assert ((self.CURRENT_PHOTO is not None and self.CURRENT_BUCKET is not None) or
              (self.CURRENT_PHOTO == self.CURRENT_BUCKET == None))

      # prime the first bucket's sort list if it hasn't been sorted yet.  add new candidate
      # photos to the sorter as well if they aren't in the system.
      if self.CURRENT_BUCKET is None:
         for bucket in self.next_bucket():
            bucket.unsorted = set(self.filelist)
            break


   ## object support methods

   def pickle(self, name, obj):
      """Serialize an object and write it out to disk"""
      pickleFile = open("files/%s" % name, "w+")
      pickle.dump(obj, pickleFile)
      pickleFile.close()

   def unpickle(self, name, objType, *objTypeArgs, **kwArgs):
      """Return deserialized object, or newly-initialized object if one doesn't exist on disk.
      If newObject is set to False, will return None if the object can't be unpickled.
      """

      # really awkward usage of args in this method; objTypeArgs tuple goes to 
      # objType ctor, but kwArgs is used here.  gross but let's just press on.
      newObject = None
      if kwArgs.has_key("newObject"):
         newObject = kwArgs["newObject"]
      else:
         newObject = True

      try:
         pickleFile = open("files/%s" % name, "r")
         obj = pickle.load(pickleFile)
      except (IOError, EOFError):
         # file does not exist; either return none or a newly initialized object
         # based on arguments
         obj = objType(objTypeArgs) if newObject is True else None
      else:
         pickleFile.close()

      return obj


   def dump(self):
      if self.dumpToDisk:
         for bucket in self.buckets:
            self.pickle("bucket-%s" % bucket.name, bucket)


   ## image transform methods

   def rotate_clockwise(self, photo, updateGui=True):
      photo.rotation = (photo.rotation + 90) % 360 # in case of 4+ rotations
      
      if updateGui:
         self.gui.redraw_window()

   def flip_horizontal(self, photo, updateGui=True):
      photo.flip_horizontal ^= True  # use xor in case of a double-flip
      
      if updateGui:
         self.gui.redraw_window()


   ## sort related methods

   def next_photo(self):
      """Generator which yields the next photo in the current bucket.  Resets
      file list is bucket changes."""
      bucket = self.CURRENT_BUCKET

      # return all the unsorted files in the given bucket, with the 
      # intent of assigning them to other buckets.  if the bucket changes
      # in between calls, then reset the candidate file list
      while True:

         # unsorted list may change on photo sort, so copy the list and
         # use that for generation.  if the list is changed, reset
         # generation.
         for f in copy(self.CURRENT_BUCKET.unsorted):
            if f in self.CURRENT_BUCKET.unsorted:
               self.CURRENT_PHOTO = f
               yield f
         break

   @classmethod
   def _tree_traverse(cls, l, pivot_list):
      if len(l) == 0:
         return

      elif len(l) == 1:
         pivot_list.append(l[0])
         return 

      pivot = l[(len(l)/2)]
      pivot_list.append(pivot)
      cls._tree_traverse(l[0:(len(l)/2)], pivot_list)
      cls._tree_traverse(l[(len(l)/2)+1:], pivot_list)

   def next_bucket(self):
      """Generator which yields a bucket to sort on.  Buckets will be handed
      back in a tree-like fashion to produce a sorting effect similar to quicksort"""
      
      # create a binary search tree of buckets
      generator_buckets = []
      self._tree_traverse(sorted(self.buckets), generator_buckets)

      for i in generator_buckets:
         self.CURRENT_BUCKET = i
         yield i


   ## event handling methods

   def sort_photo(self, photo, bucket, direction):
      """Sort a photo.  Takes a photo, current bucket, and direction.
      Direction is -1 for earlier
                    0 for unknown
                    1 for after
      """

      bucketsInOrder = []
      self._tree_traverse(sorted(self.buckets), bucketsInOrder)
      bucketsInOrder = bucketsInOrder[bucketsInOrder.index(bucket)+1:]


      earlierBuckets = [b for b in bucketsInOrder if b < bucket]
      laterBuckets = [b for b in bucketsInOrder if b > bucket]

      if direction == -1:
         bucket.unsorted.remove(photo)
         bucket.before.add(photo)

         for earlierBucket in earlierBuckets:
            earlierBucket.unsorted.add(photo)

         for laterBucket in laterBuckets:
            try:
               laterBucket.unsorted.remove(photo)
            except KeyError:
               pass

      elif direction == 0:
         bucket.unsorted.remove(photo)
         bucket.unknown.add(photo)

      elif direction == 1:
         bucket.unsorted.remove(photo)
         bucket.after.add(photo)

         for laterBucket in laterBuckets:
            laterBucket.unsorted.add(photo)

         for earlierBucket in earlierBuckets:
            try:
               earlierBucket.unsorted.remove(photo)
            except KeyError:
               pass

      else:
         raise ValueError("Invalid sort direction")

      self.merge_during()


   def merge_during(self):
      """Figure out which photos are "during" which buckets -- happens in two scenarios:

      1. a photo is after year X and before year X+<foo>
      2. a photo is after year Y, where Y is the max year
      """

      for i in range(len(self.buckets)):
         if i == 0:
            self.buckets[i].during |= self.buckets[i].after & self.buckets[i+1].before

         if i == len(self.buckets)-1:
            self.buckets[i].during |= self.buckets[i].after

         else:
            self.buckets[i].during |= self.buckets[i].after & self.buckets[i+1].before
         





class PhotoSorterGui(object):
   def __init__(self):
      self.image = None
      self.progress = None
      self.bucket = None

   def main(self):
      """Configure and run the main event loop"""
      
      self.photoSortingBackend = PhotoSorter(gui=self)

      # a few shared window elements, updateable from other methods
      self.image = gtk.Image()
      self.progressbar = gtk.ProgressBar()
      self.helpLabel = gtk.Label()
      self.sortLabel = gtk.Label()


      # set up the sorting window
      window = gtk.Window(gtk.WINDOW_TOPLEVEL)
      window.set_border_width(10)
      window.connect("delete_event", self.quit)
      window.connect("key_press_event", self.keyboard_command)
      window.show()
      window.maximize()

      vbox = gtk.VBox()
      vbox.show()
      window.add(vbox)

      self.progressbar.set_fraction(0.5)
      self.progressbar.set_text("15 of 1003")
      self.progressbar.show()
      vbox.pack_start(self.progressbar, False, False, 0)
      
      hbox = gtk.HBox()
      hbox.show()
      vbox.pack_start(hbox, False, False, 0)

      self.image.show()
      hbox.pack_start(self.image, False, False, 0)

      helpbox = gtk.VBox()
      helpbox.set_border_width(10)
      helpbox.show()
      hbox.pack_start(helpbox, False, False, 0)

      self.helpLabel.modify_font(pango.FontDescription("sans 16"))
      self.helpLabel.show()
      helpbox.pack_start(self.helpLabel, False, False, 0)

      self.sortLabel.set_justify(gtk.JUSTIFY_CENTER)
      self.sortLabel.modify_font(pango.FontDescription("sans 22"))
      self.sortLabel.show()
      vbox.pack_start(self.sortLabel, False, False, 0)

      keyLabel = gtk.Label()
      keyLabel.set_text("Press 1 for before, 2 for after")
      keyLabel.set_justify(gtk.JUSTIFY_CENTER)
      keyLabel.modify_font(pango.FontDescription("sans 18"))
      keyLabel.show()
      vbox.pack_start(keyLabel, False, False, 0)
      
      gtk.main()
   
   
   def quit(self, widget, event):
      gtk.main_quit()


   def redraw_window(self):
      pass

   def keyboard_command(self, widget, event):
      try:
         if chr(event.keyval).upper() == "A":
            pass

         if chr(event.keyval).upper() == "B":
            pass
         
         if chr(event.keyval).upper() == "N":
            pass

         if chr(event.keyval).upper() == "P":
            pass

         if chr(event.keyval) == "1":
            pass
         
         if chr(event.keyval) == "2":
            pass
         
         if chr(event.keyval) == "3":
            pass

         if chr(event.keyval).upper() == "D":
            pass

         if chr(event.keyval).upper() == "L":
            pass

         if chr(event.keyval).upper() == "H":
            pass

         if chr(event.keyval).upper() == "Q":
            self.quit(None, None)

         # resize window if necessary
         if type(widget) == gtk.Window:
            pass

      # usually happens when chr() is not in range(256), a.k.a., pressing
      # shift or ctrl key
      except ValueError:
         pass
      
      # don't propagate to inner widgets
      return True


if __name__ == "__main__":
   g = PhotoSorterGui()
   g.main()


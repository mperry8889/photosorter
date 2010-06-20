#!/usr/bin/env python
#-*- coding: iso-8859-15 -*-


import sys
import sqlite3
import os
import pygtk
pygtk.require('2.0')
import gtk
import pango
from PIL import Image as PILImage
import pickle

class PhotoSorter(object):

   def __init__(self):
      self._current_file = None
      self._current_file_index = None
      self._current_bucket = None
      self._filelist = None
      self.properties = None

      # sort buckets
      self.buckets = [1960, 1970, 1980, 1990, 2000]
      
      # unpickle data file if it exists, and load it up 
      try:
         pickleFile = open("files/data", "r")
         self.properties = pickle.load(pickleFile)
      except (IOError, EOFError):
         # file does not exist; start with empty data structure
         self.properties = {}
      else:
         pickleFile.close()


      # list of files to sort through
      self._filelist = os.listdir("files/")
      filter = lambda f: f.upper().endswith(".JPG")
      for file in self._filelist:
         if not filter(file):
            self._filelist.remove(file)


      # a few shared window elements
      self.image = gtk.Image()
      self.progressbar = gtk.ProgressBar()
      self.helpLabel = gtk.Label()
      self.sortLabel = gtk.Label()


   def prev_file(self, filter=True):
      if self._current_file_index is None:
         self._current_file_index = 0

      # can't go past 0
      if self._current_file_index <= 0:
         return self.current_file()

      self._current_file_index -= 1
      self._current_file = self._filelist[self._current_file_index]
      return self.current_file()


   def next_file(self, filter=True):
      if self._current_file is None:
         self._current_file_index = 0

      while filter is True:
         # detect last image - return None
         try:
            self._current_file = self._filelist[self._current_file_index]
         except IndexError:
            # special case: nothing left in bucket
            self._current_file_index = -1
            break
         
         self._current_file_index += 1

         # filter already-sorted items
         try:
            if self.current_bucket() in self.properties[self.current_file()]["sort"]:
               continue
            elif self.current_bucket() > max(self.properties[self.current_file()]["sort"].keys()):
               break
            elif self.current_bucket() < min(self.properties[self.current_file()]["sort"].keys()):
               break
            else:
               break

         except KeyError:
            # properties dict hasn't been constructed yet. let it slide
            break

      # return None if there's nothing left in the bucket
      if self._current_file_index == -1:
         self._current_file_index = 0
         return None

      return self.current_file()


   def current_file(self):
      return "files/%s" % self._current_file


   def next_bucket(self):
      if self._current_bucket is None:
         self._current_bucket = self.buckets[0]
      else:
         bucketno = self.buckets.index(self._current_bucket)+1
         try:
            self._current_bucket = self.buckets[bucketno]
         except IndexError:
            self._current_bucket = None

      return self._current_bucket

   def current_bucket(self):
      return self._current_bucket

   def update_bucket(self):
      bucket = self.next_bucket()

      # no, this is not the ideal way to update these labels
      self.sortLabel.set_text("Was this picture taken before or after %s?" % bucket)
      self.helpLabel.set_text(
         "Key Map:\n" +
         "  1: Before %s\n" % bucket + 
         "  2: After %s\n" % bucket + 
         "  3: Don't Know\n"
         "  L: Rotate 90°\n" +
         "  H: Flip horizontal\n" +
         "  Q: Quit\n"
      )


   def keyboard_command(self, widget, event):
      current = self.current_file()
      bucket = self.current_bucket()

      # create properties entry if it doesn't exist
      if current not in self.properties:
         self.properties[current] = {
               "filename": current,
               "rotate": 0,
               "flip_horizontal": False,
               "sort": {},
            }

      try:
         if chr(event.keyval).upper() == "A":
            print self.properties

         if chr(event.keyval).upper() == "B":
            self.update_bucket()
         
         if chr(event.keyval).upper() == "N":
            self.image.set_from_file(self.next_file(filter=False))

         if chr(event.keyval).upper() == "P":
            self.image.set_from_file(self.prev_file(filter=False))

         if chr(event.keyval) == "1":
            self.properties[current]["sort"][bucket] = "Before"
            next = self.next_file()
            if next is not None:
               self.image.set_from_file(next)
            else:
               self.update_bucket()
               self.image.set_from_file(self.next_file(filter=False))
         
         if chr(event.keyval) == "2":
            self.properties[current]["sort"][bucket] = "After"
            next = self.next_file()
            if next is not None:
               self.image.set_from_file(next)
            else:
               self.update_bucket()
               self.image.set_from_file(self.next_file(filter=False))
         
         if chr(event.keyval) == "3":
            self.properties[current]["sort"][bucket] = "Unknown"
            next = self.next_file()
            if next is not None:
               self.image.set_from_file(next)
            else:
               self.update_bucket()
               self.image.set_from_file(self.next_file(filter=False))

         if chr(event.keyval).upper() == "D":
            try:
               print self.properties[current]
            except KeyError:
               print "No properties for %s" % current

         if chr(event.keyval).upper() == "L":
            img = PILImage.open(current).rotate(90)
            img.save(current)
            self.image.set_from_file(current)
            try:
               self.properties[current]["rotate"] += 90
            except KeyError:
               self.properties[current]["rotate"] = 90

         if chr(event.keyval).upper() == "H":
            img = PILImage.open(current).transpose(PILImage.FLIP_LEFT_RIGHT)
            img.save(current)
            self.image.set_from_file(current)
            self.properties[current]["flip_horizontal"] = True

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

   def quit(self, widget, event):
      pickleFile = open("files/data", "w+")
      pickle.dump(self.properties, pickleFile)
      pickleFile.close()

      gtk.main_quit()

   def main(self):
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

      self.image.set_from_file(self.next_file(filter=True))
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
      self.update_bucket()
      self.sortLabel.show()
      vbox.pack_start(self.sortLabel, False, False, 0)

      keyLabel = gtk.Label()
      keyLabel.set_text("Press 1 for before, 2 for after")
      keyLabel.set_justify(gtk.JUSTIFY_CENTER)
      keyLabel.modify_font(pango.FontDescription("sans 18"))
      keyLabel.show()
      vbox.pack_start(keyLabel, False, False, 0)
      
      gtk.main()


if __name__ == "__main__":
   m = PhotoSorter()
   m.main()



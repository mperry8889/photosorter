#!/usr/bin/env python

import sys
import sqlite3
import os
import pygtk
pygtk.require('2.0')
import gtk
import pango
from PIL import Image as PILImage

class PhotoSorter(object):

   def __init__(self):
      self._current_file = None
      self._current_file_index = None
      self._filelist = None

      self._current_bucket = None

      self.image = gtk.Image()
      self.progressbar = gtk.ProgressBar()
      self.sortLabel = gtk.Label()

      self.buckets = ["1960", "1970", "1980", "1990", "2000"]


   def next_file(self):
      filter = lambda f: f.upper().endswith(".JPG")

      if self._current_file is None:
         self._filelist = os.listdir("files/")
         for file in self._filelist:
            if not filter(file):
               self._filelist.remove(file)
         self._current_file_index = 0

      # detect last image - return None
      try:
         self._current_file = self._filelist[self._current_file_index]
      except IndexError:
         return None
      
      self._current_file_index += 1
      return "files/%s" % self._current_file

   def current_file(self):
      return "files/%s" % self._current_file


   def next_bucket(self):
      if self._current_bucket is None:
         self._current_bucket = self.buckets[int(len(self.buckets)/2)]
      else:
         bucketno = self.buckets.index(self._current_bucket)-1
         try:
            self._current_bucket = self.buckets[bucketno]
         except IndexError:
            self._current_bucket = self.buckets[0]

      return self._current_bucket

   def current_bucket(self):
         return self._current_bucket

   def update_bucket(self):
      self.sortLabel.set_text("Was this picture taken before or after %s?" % self.next_bucket())


   def keyboard_command(self, widget, event):
      
      if chr(event.keyval).upper() == "B":
         self.update_bucket()
      
      if chr(event.keyval).upper() == "N":
         self.image.set_from_file(self.next_file())

      if chr(event.keyval) == "1":
         pass

      if chr(event.keyval) == "2":
         pass

      if chr(event.keyval).upper() == "D":
         pass

      if chr(event.keyval).upper() == "L":
         current = self.current_file()
         img = PILImage.open(current).rotate(90)
         img.save(current)
         self.image.set_from_file(current)

      if chr(event.keyval).upper() == "H":
         current = self.current_file()
         img = PILImage.open(current).transpose(PILImage.FLIP_LEFT_RIGHT)
         img.save(current)
         self.image.set_from_file(current)

      if chr(event.keyval).upper() == "S":
         print widget.get_default_size()
         print widget.get_size()
         print widget.maximize_initially


      if chr(event.keyval).upper() == "Q":
         self.quit(None, None)

      # resize window if necessary
      if type(widget) == gtk.Window:
         print "window"

      return True

   def quit(self, widget, event):
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

      self.image.set_from_file(self.next_file())
      self.image.show()
      vbox.pack_start(self.image, False, False, 0)

      self.sortLabel = gtk.Label()
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



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

      window = gtk.Window(gtk.WINDOW_TOPLEVEL)
      window.set_border_width(10)
      window.connect("delete_event", gtk.main_quit)
      window.connect("key_press_event", self.keyboard_command)
      window.show()

      vbox = gtk.VBox()
      vbox.show()
      window.add(vbox)
      
      progressbar = gtk.ProgressBar()
      progressbar.set_fraction(0.5)
      progressbar.set_text("15 of 1003")
      progressbar.show()
      vbox.add(progressbar)

      self.image = gtk.Image()
      self.image.set_from_file(self._next_file())
      self.image.show()
      vbox.add(self.image)

      sortLabel = gtk.Label()
      sortLabel.set_text("Was this photo taken before or after 1980?")
      sortLabel.set_justify(gtk.JUSTIFY_CENTER)
      sortLabel.modify_font(pango.FontDescription("sans 22"))
      sortLabel.show()
      vbox.pack_start(sortLabel, False, False, 0)

      keyLabel = gtk.Label()
      keyLabel.set_text("Press 1 for before, 2 for after")
      keyLabel.set_justify(gtk.JUSTIFY_CENTER)
      keyLabel.modify_font(pango.FontDescription("sans 18"))
      keyLabel.show()
      vbox.pack_start(keyLabel, False, False, 0)

   def _next_file(self):
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


   def keyboard_command(self, widget, event):
      if chr(event.keyval).upper() == "B":
         self.image.set_from_file("files/d00002.jpg")

      if chr(event.keyval).upper() == "N":
         self.image.set_from_file(self._next_file())

      if chr(event.keyval).upper() == "L":
         img = PILImage.open("files/d00002.jpg").rotate(90)
         img.save("files/d00002.jpg")
         self.image.set_from_file("files/d00002.jpg")

      return True


   def main(self):
      gtk.main()


if __name__ == "__main__":
   m = PhotoSorter()
   m.main()



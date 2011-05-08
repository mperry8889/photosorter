#!/usr/bin/env python
#-*- coding: iso-8859-15 -*-

import sys
import os
from PIL import Image as PILImage
import pickle
from copy import copy
from optparse import OptionParser

import pygtk
pygtk.require('2.0')

SORT_BUCKETS = [1950, 1960, 1970, 1980, 1990, 2000]

class Photo(object):
    def __init__(self, filename, bucket=None):
        self.filename = filename
        self.rotation = 0
        self.flip_horizontal = False
        self.delete = False

    def __gt__(self, rhs):
        return self.filename > rhs.filename
    def __lt__(self, rhs):
        return not self.__gt__(rhs)
    def __eq__(self, rhs):
        return self.filename == rhs.filename


class Bucket(object):
    def __init__(self, year):
        self.year = year

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

    def __gt__(self, rhs):
        return self.year > rhs.year
    def __lt__(self, rhs):
        return not self.__gt__(rhs)
    def __eq__(self, rhs):
        return self.year == rhs.year


class PhotoSorter(object):
    def __init__(self, loadFromDisk=True, dumpToDisk=True):
        self.loadFromDisk = loadFromDisk
        self.dumpToDisk = dumpToDisk

        self.CURRENT_PHOTO = None
        self.CURRENT_BUCKET = None

        # get of files to sort through and create objects
        self.filelist = os.listdir("images/")
        filter = lambda f: f.upper().endswith(".JPG") and \
                           f.startswith("0") and \
                           f.upper() is not "DONE.JPG"

        for file in self.filelist:
            if not filter(file):
                self.filelist.remove(file)
        self.photolist = [Photo("images/%s" % f) for f in self.filelist]

        if self.loadFromDisk:
            # resume sorting from point of last exit
            self.buckets = [self.unpickle("bucket-%s" % b, Bucket, b) for b in SORT_BUCKETS]

            # use the generator to wind up to the current bucket, instead of a direct
            # assignment, which doesn't restore generator state
            current_bucket = self.unpickle("current_bucket", None, newObject=False)
            if current_bucket is not None:
                for bucket in self.next_bucket():
                    if bucket == current_bucket:
                        break

        # used mostly in testing
        else:
            self.buckets = [Bucket(b) for b in SORT_BUCKETS]

            self.CURRENT_BUCKET = None

        # XXX note: the below assert fails in the case where all photos are sorted.
        # rather than making it more complicated and obscure, just comment it out
        ## bail in there case where only one of current bucket or photo is serialized but
        ## not the other; don't do any recovery, just begin manual intervention here.
        ## that shouldn't happen and it's not worth figuring out what to do there for
        ## this one-time use app.
        #assert ((self.CURRENT_PHOTO is not None and self.CURRENT_BUCKET is not None) or
        #        (self.CURRENT_PHOTO == self.CURRENT_BUCKET == None))

        # prime the first bucket's sort list if it hasn't been sorted yet.  add new candidate
        # photos to the sorter as well if they aren't in the system.
        if self.CURRENT_BUCKET is None:
            for bucket in self.next_bucket():
                bucket.unsorted = set(self.photolist)
                break

        self.PREVIOUS_PHOTO = None
        self._RESTART_PHOTO_GENERATOR = False


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
            obj = objType(*objTypeArgs) if newObject is True else None
        else:
            pickleFile.close()

        return obj

    def dump(self):
        if self.dumpToDisk:
            for bucket in self.buckets:
                self.pickle("bucket-%s" % bucket.year, bucket)

            self.pickle("current_bucket", self.CURRENT_BUCKET)


    ## image transform methods

    def rotate_clockwise(self, photo):
        photo.rotation = (photo.rotation + 90) % 360 # in case of 4+ rotations

    def flip_horizontal(self, photo):
        photo.flip_horizontal ^= True  # use xor in case of a double-flip

    def delete_photo(self, photo, bucket):
        photo.delete = True
        bucket.unsorted -= set([photo])

    ## sort related methods

    def next_photo(self):
        """Generator which yields the next photo in the current bucket.  Resets
        file list is bucket changes."""

        # self._RESTART_PHOTO_GENERATOR is a really gross way to restart the
        # photo loop from the first unsorted picture. works in the case where
        # you unsort a photo, and want to go right back to it on the next
        # iteration (since it has the "least" filename).  gross hack, too much
        # state, but these generators really aren't great for state machines,
        # which this has photo sorter turned in to.

        bucket = self.CURRENT_BUCKET

        # unsorted list may change on photo sort, so copy the list and
        # use that for generation.  if the list is changed, reset
        # generation.
        while True:
            for f in copy(sorted(self.CURRENT_BUCKET.unsorted)):
                if self._RESTART_PHOTO_GENERATOR:
                    break

                if f in self.CURRENT_BUCKET.unsorted:
                    # minor hack here (checking type) for testing
                    if type(f) is Photo and f.delete is True:
                        continue
                    else:
                        self.PREVIOUS_PHOTO = self.CURRENT_PHOTO
                        self.CURRENT_PHOTO = f
                        yield f
                else:
                    break

            if self._RESTART_PHOTO_GENERATOR:
                self._RESTART_PHOTO_GENERATOR = False
                continue
            else:
                break

        self.CURRENT_PHOTO = None


    def sort_bucket_traverse(self, bucketList):
        """Return a reordered bucket list, in the order in which yields a favorable
        comparison tree.  For the example of [1960 1970 1980 1990 2000] return
        [1980 1990 2000 1970 1960] -- start with the middle element to partition
        photos before and after an obvious year, and then bubble them outwards
        into the appropriate buckets."""

        sortedList = sorted(bucketList)
        middle = len(sortedList)/2
        returnList = [sortedList[middle]]

        for i in range(1, middle+1):

            # elements after middle
            try:
                returnList.append(sortedList[middle+i])
            except IndexError:
                pass

        for i in range(1, middle+1):

            # elements before middle
            try:
                returnList.append(sortedList[middle+(-1*i)])
            except IndexError:
                pass

        return returnList


    def next_bucket(self):
        """Generator which yields a bucket to sort on.  Buckets will be handed
        back in a tree-like fashion to produce a sorting effect similar to quicksort"""

        # create a binary search tree of buckets
        generator_buckets = self.sort_bucket_traverse(self.buckets)

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

        # in addition to sorting the photo in question, add it to the next
        # earlier or later bucket based on sort direction

        bucketsInOrder = self.sort_bucket_traverse(self.buckets)

        earlierBucket = None
        laterBucket = None
        for b in bucketsInOrder[bucketsInOrder.index(bucket)+1:]:
            # avoid a corner case where photos are added as unsorted to buckets
            # far less than the starting bucket. this happens because the bucket
            # traversal happens ascending first, then descending; so only add to
            # lower buckets if we're sorting downwards. if that makes sense.
            if b < bucket < bucketsInOrder[0]:
                earlierBucket = b
                break
        for b in bucketsInOrder[bucketsInOrder.index(bucket)+1:]:
            if b > bucket:
                laterBucket = b
                break

        # item is before the bucket date
        if direction == -1:
            bucket.unsorted.remove(photo)
            bucket.before.add(photo)

            if earlierBucket is not None:
                earlierBucket.unsorted.add(photo)

        # item is after the bucket date
        elif direction == 0:
            bucket.unsorted.remove(photo)
            bucket.unknown.add(photo)

        # item is of unknown date
        elif direction == 1:
            bucket.unsorted.remove(photo)
            bucket.after.add(photo)

            if laterBucket is not None:
                laterBucket.unsorted.add(photo)

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

    def unsort(self, photo):
        """Unsort a photo; remove it from all buckets and return it to the first bucket for 
        full re-sorting.  Strong "undo" function, since it obliterates sort state rather than
        just undoing the previous operation, but it's easy to code."""

        for bucket in self.buckets:
           bucket.unsorted -= set([photo])
           bucket.before -= set([photo])
           bucket.during -= set([photo])
           bucket.after -= set([photo])
           bucket.unknown -= set([photo])

        bucketsInOrder = self.sort_bucket_traverse(self.buckets)
        bucketsInOrder[0].unsorted.add(photo)
        self._RESTART_PHOTO_GENERATOR = True



class PhotoSorterGui(object):
    def __init__(self, maximize=False):
        self.image = None
        self.progress = None
        self.bucket = None
        self.maximize = maximize

    def main(self):
        """Configure and run the main event loop"""

        self.photoSortingBackend = PhotoSorter()
        self.bucketGenerator = self.photoSortingBackend.next_bucket()
        self.bucketGenerator.next()
        self.photoGenerator = self.photoSortingBackend.next_photo()

        # a few shared window elements, updateable from other methods
        self.image = gtk.Image()
        self.progressbar = gtk.ProgressBar()
        self.helpLabel = gtk.Label()
        self.sortLabel = gtk.Label()
        self.currentFilenameLabel = gtk.Label()
        self.sortedItems = 0
        self.totalItems = len(self.photoSortingBackend.CURRENT_BUCKET.unsorted)

        # set up the sorting window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_border_width(10)
        self.window.connect("delete_event", self.quit)
        self.window.connect("key_press_event", self.keyboard_command)
        if self.maximize:
            self.window.maximize()
        else:
            self.window.resize(1, 1)
        self.window.show()

        vbox = gtk.VBox()
        vbox.show()
        self.window.add(vbox)

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

        self.currentFilenameLabel.set_justify(gtk.JUSTIFY_LEFT)
        self.currentFilenameLabel.modify_font(pango.FontDescription("sans 14"))
        self.currentFilenameLabel.show()
        helpbox.pack_start(self.currentFilenameLabel, False, False, 0)

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

        self.redraw_window(increment=True)
        gtk.main()


    def quit(self, widget, event):
        self.photoSortingBackend.dump()
        gtk.main_quit()


    def _display_image(self):
        self.image.set_from_file(self.photoSortingBackend.CURRENT_PHOTO.filename)

        rotation = 0
        while rotation < self.photoSortingBackend.CURRENT_PHOTO.rotation:
            self.image.set_from_pixbuf(self.image.get_pixbuf().rotate_simple(gtk.gdk.PIXBUF_ROTATE_CLOCKWISE))
            rotation += 90

        if self.photoSortingBackend.CURRENT_PHOTO.flip_horizontal:
            self.image.set_from_pixbuf(self.image.get_pixbuf().flip(True))

    def redraw_window(self, increment=False):
        if increment is True:
            # use photo sorting backend's funky generators. very weird try/except
            # blocks here to detect when generators are empty.  this is hard to
            # read but does make sense.

            # keep getting new photos. if the bucket changes silently, this should
            # still keep generating photos.
            try:
                self.photoGenerator.next()

            # current bucket has no more photos
            except StopIteration:

                # explicitly increment the bucket
                try:
                    self.bucketGenerator.next()

                # out of buckets! that means everything is all done
                except StopIteration:
                    self.currentFilenameLabel.set_text("done!")
                    self.image.set_from_file("images/done.jpg")
                    return

                # show the user a dialog noting that we're going to switch buckets.
                # this has to be annoying so that it's not missed because
                # it's very important!
                dialog = gtk.Dialog("Alert! Changing Bucket",
                                    None,
                                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
                dialog.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
                dialog.set_position(gtk.WIN_POS_CENTER_ALWAYS)
                dialog.vbox.pack_start(gtk.Label(
                   "Changing the date: BE CAREFUL!\n\n" +
                   "New date is %s\n\n" % self.photoSortingBackend.CURRENT_BUCKET.year +
                   "Press Close to continue sorting.\n\n"
                ))
                dialog.show_all()
                dialog.run()
                dialog.destroy()
                self.sortedItems = 0
                self.totalItems = len(self.photoSortingBackend.CURRENT_BUCKET.unsorted)

                # since we just incremented the bucket, increment the photo
                # too since the operations are coupled. if this generator has
                # nothing left, it means the bucket has nothing unsorted in it.
                try:
                    self.photoGenerator = self.photoSortingBackend.next_photo()
                    self.photoGenerator.next()
                except StopIteration:
                    self.redraw_window(increment=increment) # XXX eats stack


        if self.photoSortingBackend.CURRENT_PHOTO is not None:
            self.currentFilenameLabel.set_text(os.path.basename(self.photoSortingBackend.CURRENT_PHOTO.filename))
            self._display_image()

        try:
            self.progressbar.set_fraction(float((1.0*self.sortedItems) / self.totalItems))
        except ZeroDivisionError:
            pass
        self.progressbar.set_text("%d of %d" % (self.sortedItems, self.totalItems))

        self.sortLabel.set_text(str(self.photoSortingBackend.CURRENT_BUCKET.year))
        self.helpLabel.set_text(
           "Keyboard Commands:\n" +
           " 1: before %s\n" % self.photoSortingBackend.CURRENT_BUCKET.year +
           " 2: after %s\n" % self.photoSortingBackend.CURRENT_BUCKET.year +
           " 3: don't know\n" +
           " H: flip horizontal\n" +
           " L: rotate 90 degrees\n" +
           " D: delete photo\n" +
           " U: undo last sort\n" +
           ""
        )
        
        if self.maximize:
            self.window.maximize()
        else:
            self.window.resize(1, 1)


    def keyboard_command(self, widget, event):

        try:
            # 1: photo is before current bucket
            if chr(event.keyval) == "1":
                if self.photoSortingBackend.CURRENT_PHOTO is not None:
                    self.photoSortingBackend.sort_photo(self.photoSortingBackend.CURRENT_PHOTO,
                                                        self.photoSortingBackend.CURRENT_BUCKET,
                                                        -1)
                    self.sortedItems += 1
                    self.redraw_window(increment=True)

            # 2: photo is after current bucket
            if chr(event.keyval) == "2":
                if self.photoSortingBackend.CURRENT_PHOTO is not None:
                    self.photoSortingBackend.sort_photo(self.photoSortingBackend.CURRENT_PHOTO,
                                                        self.photoSortingBackend.CURRENT_BUCKET,
                                                        1)
                    self.sortedItems += 1
                    self.redraw_window(increment=True)

            # 3: user doesn't know timeframe of photo
            if chr(event.keyval) == "3":
                if self.photoSortingBackend.CURRENT_PHOTO is not None:
                    self.photoSortingBackend.sort_photo(self.photoSortingBackend.CURRENT_PHOTO,
                                                        self.photoSortingBackend.CURRENT_BUCKET,
                                                        0)
                    self.sortedItems += 1
                    self.redraw_window(increment=True)

            # L: rotate photo 90 degrees.  may rotate several times.
            if chr(event.keyval).upper() == "L":
                self.photoSortingBackend.rotate_clockwise(self.photoSortingBackend.CURRENT_PHOTO)

            # H: flip photo horizontally
            if chr(event.keyval).upper() == "H":
                self.photoSortingBackend.flip_horizontal(self.photoSortingBackend.CURRENT_PHOTO)

            # U: undo last sorting operation
            if chr(event.keyval).upper() == "U":
                self.photoSortingBackend.unsort(self.photoSortingBackend.PREVIOUS_PHOTO)
                self.sortedItems -= 1

            # D: delete photo
            if chr(event.keyval).upper() == "D":
                self.photoSortingBackend.delete_photo(self.photoSortingBackend.CURRENT_PHOTO,
                                                      self.photoSortingBackend.CURRENT_BUCKET)
                self.sortedItems += 1
                self.redraw_window(increment=True)

            # Q: dump state and quit
            if chr(event.keyval).upper() == "Q":
                self.quit(None, None)
                return
            
            # X: dump information about unsorted buckets
            if chr(event.keyval).upper() == "X":
                for bucket in self.photoSortingBackend.buckets:
                    print bucket.year, [b.filename for b in bucket.unsorted]


            # Z: move "unknown" photos to "unsorted"
            if chr(event.keyval).upper() == "Z":
                for bucket in self.photoSortingBackend.buckets:
                    bucket.unsorted |= bucket.unknown
                    bucket.unknown = set([])

                # modify internal state variable... shhhh
                self.photoSortingBackend._RESTART_PHOTO_GENERATOR = True

        # usually happens when chr() is not in range(256), a.k.a., pressing
        # shift or ctrl key
        except ValueError:
            pass

        self.redraw_window(increment=False)

        # don't propagate to inner widgets
        return True


if __name__ == "__main__":
    import gtk
    import pango
    maximize = False
    if "-m" in sys.argv[1:]:
        maximize = True

    g = PhotoSorterGui(maximize=maximize)
    g.main()


#!/usr/bin/env python

from photosorter import PhotoSorter
from photosorter import Bucket
from photosorter import Photo

if __name__ == "__main__":
    p = PhotoSorter()

    for bucket in p.buckets:
        for state in ["during", "after", "before", "unknown", "unsorted"]:
            for photo in getattr(bucket, state):
                print "%s %s %s %s %s" % (state, bucket.year, photo.filename, photo.rotation, photo.flip_horizontal)


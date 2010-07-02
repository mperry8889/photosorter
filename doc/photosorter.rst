==================
 Photo Sorter 1.0
==================

------------
 Motivation
------------

 It's daunting to find a particular photo in a set of 6,100 scanned images which lack EXIF data.  
 Sorting photos into buckets of 10 years makes this at least a little bit easier, and allows photo viewing apps (namely `Picasa <http://picasa.google.com>`_) to show groups of photos from the 70s, 80s, 90s, etc.


--------------
 How It Works
--------------

 An image and a year is displayed to the user, and the user decides whether the photo occurred before the given year or after the given year.  Once the user has compared all of the photos to that year (e.g. 1980), then the year is changed and applicable photos are compared to the new one (e.g. 1990).

 When an image is after year A and before year B, it is considered to be "during" year A.

-------
 Notes
-------
 
 * Buckets are set in the ``SORT_BUCKETS`` variable in the code; there are no other ways to change the buckets.
 * Unit tests require some JPG files to be present in the ``images/`` subdirectory.

-------------
 Limitations
-------------

 * Works with more than 2 buckets only


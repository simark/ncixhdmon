ncixhdmon
=========

**ncixhdmon** helps you choose a hard drive to buy from NCIX. It fetches the list
of hard drives from [ncix.com](http://www.ncix.com/), computes the cost per GB and
outputs a simple sorted list.

A weekly updated list can generally be found [here](http://nova.polymtl.ca/~simark/ncixhd.txt).

you need
--------

  * Python 3
    * BeautifulSoup 4
    * Jinja2

use it
------

Plain text report:

    python ncixhdmon.py

HTML report:

    python ncixhdmon.py html > /tmp/report.htm && your-favorite-browser /tmp/report.htm

With a size limit of 1000 GB:

    python ncixhdmon.py text 1000
    python ncixhdmon.py html 1000 > /tmp/report.htm && your-favorite-browser /tmp/report.htm

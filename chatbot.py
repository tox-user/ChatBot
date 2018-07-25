#!/usr/bin/python

from os.path import exists
from core import Core
from toxoptions import ToxOptions

options = ToxOptions()

if exists(options.profile):
	options.load_profile()


core = Core(options)
core.loop()

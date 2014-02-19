from __future__ import division, print_function
# Python
from collections import OrderedDict, defaultdict
from os.path import (dirname, realpath, join, exists, normpath, splitext,
                     expanduser, relpath)
import imp
import itertools
from itertools import izip, chain
from itertools import product as iprod
import multiprocessing
import os
import re
import sys
import site
import shutil
# Matplotlib
import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt
# Scientific
import numpy as np
import networkx as netx
from PIL import Image
from PIL.ExifTags import TAGS
import cv2
from scipy.cluster.hierarchy import fclusterdata
# Qt
import PyQt4
from PyQt4 import QtCore, QtGui
from PyQt4.Qt import (QAbstractItemModel, QModelIndex, QVariant, QWidget,
                      Qt, QObject, pyqtSlot, QKeyEvent)
# HotSpotter
from hotspotter import Config
from hotspotter import DataStructures as ds
from hotspotter import HotSpotterAPI
from hotspotter import HotSpotterAPI as api
from hotspotter import QueryResult as qr
from hotspotter import algos
from hotspotter import extern_feat
from hotspotter import db_info
from hotspotter import chip_compute2 as cc2
from hotspotter import feature_compute2 as fc2
from hotspotter import load_data2 as ld2
from hotspotter import match_chips3 as mc3
from hotspotter import matching_functions as mf
from hotspotter import nn_filters
from hotspotter import QueryResult as qr
from hotspotter import report_results2 as rr2
from hotspotter import segmentation
from hotspotter import spatial_verification2 as sv2
from hotspotter import voting_rules2 as vr2
#
from hsgui import guiback
from hsgui import guifront
from hsgui import guitools
#
from hscom import __common__
from hscom import Parallelize as parallel
from hscom import Preferences as prefs
from hscom import Printable
from hscom import argparse2
from hscom import cross_platform as cplat
from hscom import fileio as io
from hscom import helpers
from hscom import helpers as util
from hscom import latex_formater
from hscom import params
from hscom import tools
#
from hsviz import draw_func2 as df2
from hsviz import extract_patch
from hsviz import viz
from hsviz import interact
from hsviz import allres_viz
#
from hstpl import mask_creator as mc
# DEV
from hsdev import dev_stats
from hsdev import dev_consistency
from hsdev import dev_api
from hsdev import dev_reload
#
import dev

if __name__ == 'main':
    multiprocessing.freeze_support()
    #exec(open('dbgimport.py').read())
    if '--img' in sys.argv:
        img_fpath_ = helpers.dbg_get_imgfpath()
        np_img_ = io.imread(img_fpath_)
        img_ = Image.open(img_fpath_)

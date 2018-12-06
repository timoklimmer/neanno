import os
import sys

import pandas as pd

from neanno.configuration import Configuration
from neanno.models import TextModel
from neanno.ui import AnnotationDialog

def main():
    try:
        # run the annotation dialog
        AnnotationDialog(TextModel())
    except:
        print("An unhandled error occured: ", sys.exc_info()[0])
        raise

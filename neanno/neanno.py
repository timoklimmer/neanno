import sys

from neanno.models.textmodel import TextModel
from neanno.ui.annotationdialog import AnnotationDialog

def main():
    try:
        # run the annotation dialog
        AnnotationDialog(TextModel())
    except:
        print("An unhandled error occured: ", sys.exc_info()[0])
        raise

from pandas import DataFrame
import glob
import sys, os
DQ_PATH = "DQ"

def collect_rules():
    glob_rules = glob(os.path.join(QD_PATH, "*.py"))
    

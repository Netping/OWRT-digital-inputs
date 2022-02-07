#!/usr/bin/python3
import os
import sys
import argparse

version = '0.1'

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--version", required=True, help="version of test module")
args = vars(ap.parse_args())
if args['version'] != version:
    print("Wrong version! Expected \"" + version + "\"")
    sys.exit(-2)

if __name__ == "__main__":

    print('OWRT-Digital-inputs')
    print('version ' + version)
    os.system("pytest --capture=no -v test.py")
    sys.exit(0)
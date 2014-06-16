import os
import sys
import urllib
import tarfile

def file_name_from_url(url, directory=None):
    file_name = url.split('/')[-1]
    if directory:
        file_name = os.path.join(directory, file_name)
    return file_name

def download_tar(url, directory=None):
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_name = file_name_from_url(url, directory)
    print "Downloading {} to {}".format(url, file_name)
    sys.stdout.flush()
    urllib.urlretrieve(url, file_name)

def extract_contents(file_name, destination='.'):
    if not os.path.exists(destination):
        os.makedirs(destination)

    print "Extracting {} to {}".format(file_name, destination)
    sys.stdout.flush()
    tar = tarfile.open(file_name)
    tar.extractall(destination)
    tar.close()

def download_and_extract(url, directory=None):
    download_tar(url, directory)
    extract_contents(file_name_from_url(url, directory), directory)

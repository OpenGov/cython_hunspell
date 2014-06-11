import os
import sys
import glob
import shutil
import imp
from setuptools import setup, find_packages, Extension
from distutils.command.install import install
from subprocess import check_call
from scripts.find_library import pkgconfig

VERSION = '1.0.1'

requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')

skip_pip_call = '--no-pre-pip'
if skip_pip_call not in sys.argv:
    check_call('pip install -r {}'.format(requirements_file), stdout=sys.stdout, stderr=sys.stderr, shell=True)
else:
    sys.argv = [arg for arg in sys.argv if arg != skip_pip_call]

from Cython.Build import cythonize
from Cython.Distutils import build_ext

def read(fname):
    # Utility function to read the README file.
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def readMD(fname):
    # Utility function to read the README file.
    full_fname = os.path.join(os.path.dirname(__file__), fname)
    if 'PANDOC_PATH' in os.environ:
        import pandoc
        pandoc.core.PANDOC_PATH = os.environ['PANDOC_PATH']
        doc = pandoc.Document()
        with open(full_fname) as fhandle:
            doc.markdown = fhandle.read()
        return doc.rst
    else:
        return read(fname)

datatypes = ['*.aff', '*.dic', '*.txt']
packages = find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests'])
packages.append('dictionaries')
required = [req.strip() for req in read('requirements.txt').splitlines() if req.strip()]

ext_modules = cythonize([
    Extension(
        os.path.join(os.path.dirname(__file__), 'hunspell', 'hunspell'),
        [os.path.join(os.path.dirname(__file__), 'hunspell', 'hunspell.pyx')],
        extra_compile_args=['-O3', '-g0'],
        **pkgconfig('hunspell', language='c++')
    )
])

setup(
    name='CyHunspell',
    version=VERSION,
    author='Matthew Seal',
    author_email='mseal@opengov.us',
    description='A wrapper on hunspell for use in Python',
    long_description=readMD('README.md'),
    ext_modules=ext_modules,
    install_requires=required,
    cmdclass={ 'build_ext': build_ext },
    license='New BSD',
    packages=packages,
    include_package_data=True,
    test_suite='tests',
    zip_safe=False,
    url='https://github.com/OpenGov/cython_hunspell',
    download_url='https://github.com/OpenGov/cython_hunspell/tarball/v' + VERSION,
    package_data={'' : datatypes},
    keywords=['hunspell', 'spelling', 'correction'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2 :: Only'
    ]
)

# CyHunspell
Cython wrapper on Hunspell Dictionary

## Description
This repository provides a wrapper on Hunspell to be used natively in Python. The module uses
cython to link between the C++ and Python code, with some additional features. The hunspell
library will cache any corrections, you can use persistent caching by adding the `use_disk_cache`
argument to a Hunspell constructor, otherwise it uses in-memory caching.

NOTE: This repository only works on Unix environments until pthreads can be replicated with an
mthread implementaiton.

## Dependencies
cacheman -- for persistent caching

## Features
* See http://hunspell.sourceforge.net/

## How to use
Below are some simple examples for how to use the repository.

### TODO FILL IN

## Navigating the Repo
### hunspell
Package wrapper for the repo.

### tests
All unit tests for the repo.

## Language Preferences
* Google Style Guide
* Object Oriented (with a few exceptions)

## TODO
* Add mthreads alongside pthreads for bulk operations
* Fix blocking issues for Windows usage (see above)
* Remove cacheman dependency

## Author
Author(s): Tim Rodriguez and Matthew Seal

&copy; Copyright 2014, [OpenGov](http://opengov.com)

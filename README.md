[![Build Status](https://travis-ci.org/OpenGov/cython_hunspell.svg?branch=master)](https://travis-ci.org/OpenGov/cython_hunspell)

# CyHunspell
Cython wrapper on Hunspell Dictionary

## Description
This repository provides a wrapper on Hunspell to be used natively in Python. The
module uses cython to link between the C++ and Python code, with some additional
features. There's very little Python overhead as all the heavy lifting is done
on the C++ side of the module interface, which gives optimal performance.

The hunspell library will cache any corrections, you can use persistent caching by
adding the `use_disk_cache` argument to a Hunspell constructor. Otherwise it uses
in-memory caching.

## Dependencies
cacheman -- for (optionally asynchronous) persistent caching

## Features
Spell checking & spell suggestions
* See http://hunspell.sourceforge.net/

## How to use
Below are some simple examples for how to use the repository.

### Creating a Hunspell object
    from hunspell import Hunspell
    h = Hunspell();

You now have a usable hunspell object that can make basic queries for you.

    h.spell('test') # True

### Spelling
It's a simple task to ask if a particular word is in the dictionary.

    h.spell('correct') # True
    h.spell('incorect') # False

This will only ever return True or False, and won't give suggestions about why it
might be wrong. It also depends on your choice of dictionary.

### Suggestions
If you want to get a suggestion from Hunspell, it can provide a corrected label
given a basestring input.

    h.suggest('incorect') # (u'incorrect', u'correction', u'corrector', u'correct', u'injector')

The suggestions are in sorted order, where the lower the index the closer to the
input string.

### Stemming
The module can also stem words, providing the stems for pluralization and other
inflections.

    h.stem('testers') # (u'tester', u'test')
    h.stem('saves') # (u'save',)

### Bulk Requests
You can also request bulk actions against Hunspell. This will trigger a threaded
(without a gil) request to perform the action requested. Currently just 'suggest'
and 'stem' are bulk requestable.

    h.bulk_suggest(['correct', 'incorect'])
    # {'incorect': (u'incorrect', u'correction', u'corrector', u'correct', u'injector'), 'correct': ['correct']}
    h.bulk_stem(['stems', 'currencies'])
    # {'currencies': [u'currency'], 'stems': [u'stem']}

By default it spawns number of CPUs threads to perform the operation. You can
overwrite the concurrency as well.

    h.set_concurrency(4) # Four threads will now be used for bulk requests

### Dictionaries
You can also specify the language or dictionary you wish to use.

    h = Hunspell('en_CA') # Canadian English

By default you have the following dictionaries available
* en_AU
* en_CA
* en_GB
* en_NZ
* en_US
* en_ZA

However you can download your own and point Hunspell to your custom dictionaries.

    h = Hunspell('en_GB-large', hunspell_data_dir='/custom/dicts/dir')

### Asynchronous Caching
If you want to have Hunspell cache suggestions and stems you can pass it a directory
to house such caches.

    h = Hunspell(disk_cache_dir='/tmp/hunspell/cache/dir')

This will save all suggestion and stem requests periodically and in the background.
The cache will fork after a number of new requests over particular time ranges and
save the cache contents while the rest of the program continues onward. You'll never
have to explicitly save your caches to disk, but you can if you so choose.

    h.save_cache()

Otherwise the Hunspell object will cache such requests locally in memory and not
persist that memory.

## Platforms
### Linux
Tested on Ubuntu and Fedora with pre-build binaries of Hunspell as well as
automatically build depedencies. It's inlikely to have trouble with other
distributions.

### Windows
The base library comes with MSVC built Hunspell libraries and will link
against those during runtime. These were tested on Windows 7, 8, 10 and
some on older systems. It's possible that a Python build with a newer
(or much older) version of MSVC will fail to load these pre-built libraries.

### Mac OSX
So far the library has been tested against 10.9 (Mavericks) and up. There
shoudn't be any reason it would fail to run on any particular version of
OSX.

## Navigating the Repo
### hunspell
Package wrapper for the repo.

### tests
All unit tests for the repo.

## Language Preferences
* Google Style Guide
* Object Oriented (with a few exceptions)

## TODO
* Convert cacheman dependency to be optional

## Author
Author(s): Tim Rodriguez and Matthew Seal

## License
MIT

&copy; Copyright 2015, [OpenGov](http://opengov.com)

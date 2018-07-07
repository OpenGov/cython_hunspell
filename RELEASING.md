Update the CHANGELOG.md with any significant changes for the release.

Then ensure that you've built the extension for the release.

    python --version # Should be 3.6.x -- change if not in 3.6
    pip install -r requirements-dev.txt
    python setup.py build_ext
    python setup.py test # Should pass with changes

You should now see a new hunspell.cpp in the hunspell directory.

   git add hunspell/hunspell.cpp
   git commit -m "Compiled new hunspell.cpp for release"

To release, run through the following:

    rm -rf dist
    # Update VERSION file with <next version>
    git tag <next version>
    python setup.py sdist
    # Check the tar version matches expected release version
    git push --tags
    twine upload dist/*

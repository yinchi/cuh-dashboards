#!/usr/bin/env bash

# Builds Sphinx documentation.
# WARNING: only works if project is in a git repository.

set -e
pushd `git rev-parse --show-toplevel`

ls

pushd documentation
make clean
rm -rf ./source/apidoc
sphinx-apidoc -feM -o ./source/apidoc ../hpath
make html
popd

rsync -avz --delete ./documentation/build/html/ ./docs

popd

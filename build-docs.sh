#!/usr/bin/env bash

# Builds Sphinx documentation.
# WARNING: only works if project is in a git repository.

set -e
pushd `git rev-parse --show-toplevel`
pushd docs

make clean
rm -rf ./source/apidoc
sphinx-apidoc -feM -o ./source/apidoc ../hpath
make html

popd
popd

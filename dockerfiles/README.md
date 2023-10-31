This directory contains Dockerfiles for building the various services of the dashboards app.

The files with "-dev" suffixes are for development and use bind mounts to sync the host and
container filesystems.  The files with no "-dev" suffix are for production purposes and generate
a copy of the required application files/directories instead.

`alias.sh` in the project root directory contains the `dev` and `prod` aliases
to simplify working with Docker Compose.

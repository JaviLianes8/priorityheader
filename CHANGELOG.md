# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release: parse and build the HTTP Priority header (RFC 9218), with the
  `u` urgency and `i` incremental members read from and written to an RFC 8941
  structured-field dictionary, defaults applied on parse and omitted on build.

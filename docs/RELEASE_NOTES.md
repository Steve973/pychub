# Release Notes

This file contains the release notes for pychub. If anyone is interested in the
details or inspiration for the changes as pychub progresses, you can find them
here.

You can find more information in the [Changelog](CHANGELOG.md). 

## Version 2.0.0

Corresponds to the [2.0.0 changelog entry](CHANGELOG.md#200-unreleased).

I have been using pychub in my data science platform, and I realized that I need
to make some breaking changes to accommodate some things that I did not foresee
when I completed the initial implementation in 1.x.

1. I did not think about packaging dependency wheels that are set up as path
   dependencies. Until this point, pychub looks only at pypi to resolve any of
   the dependency wheels when building a chub file. I realized that I need to
   support local wheel resolution, and this version introduces that feature.

2. Pychub is able to look at a `chubproject.toml` file for the configuration
   of the archive. Previous to this release, it was much too lenient in its
   discovery of the table or section of the toml file. This showed me that I
   needed to make this discovery (and format) stricter. In a `pyproject.toml`
   file, the section must only/always be `[tool.pychub.pacakge]`. When you use
   a `chubproject.toml` file, it is more lenient, but still fairly strict. The
   table can be named `[tool.pychub.package]`, `[pychub.package]`, or
   `[package]`. It is also permissible to omit a top-level table header
   entirely. The default is `[tool.pychub.package]`.

## Version 1.x.x

Corresponds to the [1.x.x changelog entry](CHANGELOG.md#1xx-initial-release--updates).

The initial release. Pychub was inspired by my need for an easy way to package
and deploy wheels and their dependencies. I had been working on a platform that
uses both Java and Python, and the plugin system needed a way to pacakge the
plugins.

My use case guided the development, but I wanted to remove assumptions and the
specifics of my use case so that it could be useful to other people. There are
no tools that do exactly what I wanted to make pychub do. I saw that there was
a niche for it, and that it would be a good tool for others if they need
something that simplified packaging without the extra things that many of the
other tools do.
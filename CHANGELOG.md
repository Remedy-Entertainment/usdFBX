# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2023-07-21
### Added
- Support for Materials
  - Lambert and Phong Materials are transferred as well as possible into UsdPreview shaders and setups. Not everything that FBX supports is supported by USD and vice versa.
  - Notable points of interest: 
    - `Shininess` vs `inputs:roughness` - There seems to be little consistency inside FBX and DCCs that output FBX what value range `Shininess` should adhere to. The plugin makes efforts to remap to a `0..1` range depending on the current value. Conversion to `inputs:roughness` is a linear inversion
    - `Opacity` and `TransparencyFactor` vs `inputs:opacity` - As with `Shininess`, the validity of how `Opacity` and `TransparencyFactor` properties are written into an FBX file depends entirely on who is writing it. The plugin maps `Opacity` from FBX into UsdPreview's `inputs:opacity` attribute directly. It seemed to be at least the most stable avenue as some DCCs only author `TransparencyFactor` and others do the same but use `TransparencyFactor` as it were `Opacity`
  - Tests
- Support for multiple `displayColor`s
  - Multiple sets of vertex colors are transferred over as multiple `primvars:displayColors_<name>` attributes
  - `primvars:displayColors` is set to the first color set iterated over
  - Tests
- Tests for geometry changes on when FBXs have been exported with non Y-up axis and differing Units
- Tests for sanitized names

### Fixed
- There was an issue where FBX Nodes that do not directly represent a prim could cause errors with `SdfPath` due to how they were named. The plugin now tries to sanitize all names where possible so that they are `SdfPath` friendly
- Crash with single joint skeleton

### Changed
- Prefer `primvars:normals` and `primvars:tangents` over their `UsdGeom` counterparts
- Skeleton tests now validate the transformations as well
- Version management is now done via a generated VERSION file

## [1.0.0] - 2023-06-28
### Added 
- Initial project import from Remedy
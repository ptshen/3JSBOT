# webgl_loader_texture_ktx2.jpg

# Three.js Scene Description: Uncompressed Texture Formats

## Overview
This scene demonstrates three different uncompressed texture format variations used in WebGL/Three.js, displayed as a comparative study of data loading and memory efficiency.

## Scene Composition

**Three Identical Green Cubes** arranged horizontally across the viewport, each labeled with a specific texture format:

### Left Cube
- **Label**: `ktx2_rgbah.ktx2`
- **Format**: RGBA with alpha channel
- **Characteristics**: Full color and transparency information, larger file size

### Center Cube
- **Label**: `ktx2_rgbak_linear.ktx2`
- **Format**: RGBA with alpha, linear color space
- **Characteristics**: Linear color space variant, maintaining full channel data with gamma-corrected rendering

### Right Cube
- **Label**: `ktx2_rgbak_srgb.ktx2`
- **Format**: RGBA with alpha, sRGB color space
- **Characteristics**: Standard sRGB color space, optimized for perceptual color accuracy

## Visual Properties
- **Geometry**: Uniform cube primitives
- **Material**: Bright green (#00AA00 or similar) flat shading
- **Lighting**: Simple, even illumination with no shadows
- **Layout**: Symmetrical horizontal arrangement with consistent spacing

## Technical Context
The scene illustrates how KTX2 container formats handle uncompressed texture data, comparing color space handling and storage efficiency—useful for WebGL developers optimizing texture assets for real-time 3D applications.

# webgpu_texturegrad.jpg

# Three.js Scene Description

## Overview
This scene displays two identical **color gradient palettes** rendered as 3D cube meshes, positioned side-by-side against a dark gray background. Each palette demonstrates smooth color transitions across the RGB color space.

## Technical Details

### Geometry & Structure
- **Composition**: Each palette consists of a grid of small cubes arranged in a square matrix (appears to be approximately 12x12 cubes)
- **Layout**: The cubes are tightly packed without visible gaps, creating a unified color field
- **Positioning**: Left palette positioned in the left-center area; right palette mirrored on the right-center area with equal spacing from center

### Color Mapping
The gradients follow a systematic color distribution:
- **Top-Left**: Magenta/Pink tones
- **Top-Right**: Blue/Cyan tones
- **Bottom-Left**: Red/Coral tones
- **Bottom-Right**: Green tones
- **Center transitions**: Smooth interpolation through purple, cyan, and neutral gray areas

### Lighting & Materials
- **Material**: Appears to be standard Lambert or Phong material with matte appearance
- **Lighting**: Soft, even illumination with subtle shading on cube faces, suggesting default three.js lighting setup
- **No shadows**: Clean presentation without shadow mapping

### Scene Context
- **Background**: Uniform dark charcoal (#3a3a3a or similar)
- **Purpose**: Educational color space visualization or RGB palette demonstration

This is a classic three.js example commonly used for teaching 3D graphics, color theory, or WebGL fundamentals.

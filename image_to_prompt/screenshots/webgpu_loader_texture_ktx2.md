# webgpu_loader_texture_ktx2.jpg

# Three.js Scene Description: Uncompressed RGBA Textures

## Scene Overview
This is a technical demonstration showcasing three uncompressed RGBA texture formats in Three.js, displayed as three distinct 3D objects arranged horizontally across the viewport.

## Visual Composition

**Layout**: Three identical green square/cube objects positioned side-by-side with even spacing and symmetrical arrangement.

**Color Scheme**: 
- Dominant vibrant lime/neon green (#00FF00 or similar) for the primary geometry
- Neutral light gray background
- White text labels

## Individual Objects (Left to Right)

1. **Left Object**: "REC_02_rgba8.ktx2"
   - Colorspace: sRGB
   - Format designation indicating 8-bit RGBA compression

2. **Center Object**: "REC_02_rgba8_linear.ktx2"
   - Colorspace: linear
   - RGBA 8-bit format with linear color space

3. **Right Object**: "REC_02_rgba8_linear.ktx2"
   - Colorspace: sRGB-linear
   - Hybrid color space specification

## Technical Context
The scene illustrates texture format variations using `.ktx2` container format, demonstrating how identical geometry appears under different RGBA texture configurations and color space treatments—useful for comparing rendering quality and performance characteristics in WebGL/Three.js applications.

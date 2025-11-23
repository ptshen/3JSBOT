# webgl_reversed_depth_buffer.jpg

# Three.js Scene Description

## Overview
This is a technical visualization demonstrating three different **depth buffer rendering techniques** in three.js, displayed side-by-side for comparison.

## Scene Layout

### Three Columns
The scene is divided into three equal sections, each showcasing a different z-buffer approach:

1. **Left: Normal Z-Buffer**
   - Standard depth rendering technique
   - Shows typical depth-based occlusion

2. **Center: Logarithmic Z-Buffer**
   - Enhanced depth precision distribution
   - Improved handling of objects at varying distances
   - Better for scenes with extreme depth ranges

3. **Right: Reverse Z-Buffer**
   - Alternative depth testing method
   - Optimized near-plane precision
   - Modern technique for improved numerical stability

## Visual Elements

### Repeated Stacked Objects
Each column contains **4 horizontally-stacked rectangular bars** arranged vertically. Each bar displays:
- **Red section** (left half)
- **Green section** (right half)

This repetition across columns allows direct visual comparison of how each technique handles the same geometry and depth information.

## Color Scheme
- **Black background** - Provides contrast for technical analysis
- **Red and green colored primitives** - Clearly distinguishes the test geometry
- **Yellow text overlay** - Informational labels and warnings

## Technical Context
The yellow text at the top notes that a **floating-point depth buffer with PNG processing** is recommended for accurate visualization and precision in depth calculations.

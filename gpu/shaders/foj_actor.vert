#version 450 core
/* FoJ clean-room GPU research shader source.
 * FojGpuVertex layout: 6 float32s in a single vertex stream.
 * Input locations: (0) clip-space xyzw; (1) UV.
 * Geometry and textures are supplied only by the user's local files.
 */
layout(location=0) in vec4 aClipPosition;
layout(location=1) in vec2 aUV;
layout(location=0) out vec2 vUV;

void main() {
    gl_Position = aClipPosition;
    vUV = aUV;
}

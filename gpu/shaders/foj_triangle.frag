#version 450 core
/* Synthetic deko3d texture sampling research. Two generated RGBA8
 * images are bound separately by the material index of each draw batch.
 * No original Vandal Hearts textures or game data are used here. */
layout(location=0) in vec2 vUV;
layout(location=0) out vec4 oColor;
layout(binding=0) uniform sampler2D uResearchMaterial;

void main() {
    oColor = texture(uResearchMaterial, vUV);
}

#version 450 core
/* Stage264 invented-only alpha cutout. Discarded fragments MUST NOT write
 * depth; opaque fragments retain Stage263 GREATER depth/write behavior.
 * This is not alpha blending or original FoJ material equivalence. */
layout(location=0) in vec2 vUV;
layout(location=0) out vec4 oColor;
layout(binding=0) uniform sampler2D uResearchMaterial;

void main() {
    vec4 texel=texture(uResearchMaterial,vUV);
    if (texel.a < 0.5) discard;
    oColor=texel;
}

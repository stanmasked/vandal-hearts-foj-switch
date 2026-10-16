#version 450 core
/* One original-user-supplied DDS atlas is bound per draw batch.
 * Experimental nearest/bilinear and alpha cutout are sampler/pipeline
 * choices, not verified original PS3 material behavior.
 */
layout(location=0) in vec2 vUV;
layout(location=0) out vec4 oColor;
layout(binding=0) uniform sampler2D uAtlas;

void main() {
    vec4 texel = texture(uAtlas, vUV);
    if (texel.a < (128.0 / 255.0)) discard;
    oColor = vec4(texel.rgb, 1.0);
}

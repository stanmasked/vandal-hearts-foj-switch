/* Deterministic host-side checks for a synthetic tile renderer. */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "tactical_demo.h"
#include "isometric_demo.h"

static uint64_t fingerprint(const uint32_t *pixels, size_t count) {
    uint64_t hash = UINT64_C(1469598103934665603);
    for (size_t i = 0; i < count; ++i) {
        hash ^= pixels[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static void test_projection(void) {
    int x, y;
    foj_iso_project(1280, 720, 1, 2, 0, &x, &y);
    assert(x == 586 && y == 210);
    foj_iso_project(1280, 720, 1, 2, 2, &x, &y);
    assert(x == 586 && y == 174);
}

static void test_render_and_reachable_highlights(void) {
    const int width = 1280, height = 720;
    const size_t count = (size_t)width * (size_t)height;
    uint32_t *pixels = calloc(count, sizeof(*pixels));
    assert(pixels);
    FojDemo state;
    foj_demo_init(&state);

    foj_iso_render(&state, pixels, width, height, width);
    const uint64_t baseline = fingerprint(pixels, count);
    assert(pixels[0] == UINT32_C(0xff21130d)); /* background */
    size_t changed = 0;
    for (size_t i = 0; i < count; ++i) {
        if (pixels[i] != UINT32_C(0xff21130d)) ++changed;
    }
    assert(changed > 10000);

    state.selected = true;
    foj_iso_render(&state, pixels, width, height, width);
    assert(fingerprint(pixels, count) != baseline);

    state.cursor_x = 3;
    state.cursor_y = 2;
    foj_iso_render(&state, pixels, width, height, width);
    assert(fingerprint(pixels, count) != baseline);
    free(pixels);
}

static void test_tiny_canvas_and_padded_stride(void) {
    enum { WIDTH = 48, HEIGHT = 32, STRIDE = 53 };
    uint32_t pixels[HEIGHT * STRIDE];
    for (size_t i = 0; i < (size_t)HEIGHT * STRIDE; ++i)
        pixels[i] = UINT32_C(0x12345678);
    FojDemo s;
    foj_demo_init(&s);
    foj_iso_render(&s, pixels, WIDTH, HEIGHT, STRIDE);
    for (int y = 0; y < HEIGHT; ++y) {
        for (int x = WIDTH; x < STRIDE; ++x)
            assert(pixels[y * STRIDE + x] == UINT32_C(0x12345678));
    }
    assert(pixels[0] != UINT32_C(0x12345678));

    /* Invalid stride must not touch the buffer. */
    pixels[0] = UINT32_C(0x12345678);
    foj_iso_render(&s, pixels, WIDTH, HEIGHT, WIDTH - 1);
    assert(pixels[0] == UINT32_C(0x12345678));
}

int main(void) {
    test_projection();
    test_render_and_reachable_highlights();
    test_tiny_canvas_and_padded_stride();
    puts("Synthetic isometric renderer checks passed (three scenarios)");
    return 0;
}

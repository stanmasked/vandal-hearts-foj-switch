/*
 * Off-console screenshot reference: write RGB PPM using the exact portable
 * isometric rasterizer linked into the Switch NRO.
 *
 * Invented tactical test data, NOT a Vandal Hearts PS3 screenshot.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tactical_demo.h"
#include "isometric_demo.h"

enum { PREVIEW_WIDTH = 1280, PREVIEW_HEIGHT = 720 };

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3) {
        fprintf(stderr, "Usage: %s OUTPUT.ppm [selected]\n", argv[0]);
        return 2;
    }
    FojDemo demo;
    foj_demo_init(&demo);
    if (argc == 3) {
        if (strcmp(argv[2], "selected") != 0) {
            fprintf(stderr, "Optional mode must be 'selected'\n");
            return 2;
        }
        demo.selected = true;
        demo.cursor_x = 3;
        demo.cursor_y = 2;
    }
    const size_t count = (size_t)PREVIEW_WIDTH * PREVIEW_HEIGHT;
    uint32_t *framebuffer = calloc(count, sizeof(uint32_t));
    if (!framebuffer) return 3;
    foj_iso_render(&demo, framebuffer, PREVIEW_WIDTH, PREVIEW_HEIGHT, PREVIEW_WIDTH);

    FILE *file = fopen(argv[1], "wb");
    if (!file) {
        perror("Cannot open preview output");
        free(framebuffer);
        return 4;
    }
    int okay = fprintf(file, "P6\n%d %d\n255\n", PREVIEW_WIDTH, PREVIEW_HEIGHT) > 0;
    for (size_t i = 0; i < count && okay; ++i) {
        uint32_t pixel = framebuffer[i];
        const unsigned char rgb_bytes[3] = {
            (unsigned char)(pixel & 0xff),
            (unsigned char)((pixel >> 8) & 0xff),
            (unsigned char)((pixel >> 16) & 0xff)
        };
        okay = fwrite(rgb_bytes, 1, 3, file) == 3;
    }
    if (fclose(file) != 0) okay = 0;
    free(framebuffer);
    return okay ? 0 : 5;
}

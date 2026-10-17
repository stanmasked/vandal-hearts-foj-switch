/* Generated-only native DDS acceptance oracle for stage-161 Python tests.
 * Parses arbitrary local fixture bytes with the actual GPU atlas decoder.
 * Does not print source filenames, pixels, or private file information.
 * NOT a production PS3 extractor or a Nintendo Switch emulator. */
#include "atlas_dds.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    FILE *fp = fopen(argv[1], "rb");
    if (!fp) return 2;
    int code = 2;
    uint8_t *blob = NULL;
    uint8_t *pixels = NULL;
    if (fseek(fp, 0, SEEK_END) != 0) goto done;
    const long length = ftell(fp);
    if (length < 0 || (unsigned long)length >
          FOJ_ATLAS_DDS_HEADER_BYTES + FOJ_ATLAS_MAX_INPUT_BYTES) goto done;
    if (fseek(fp, 0, SEEK_SET) != 0) goto done;
    blob = (uint8_t *)malloc((size_t)length + 1);
    pixels = (uint8_t *)malloc(FOJ_ATLAS_MAX_BYTES);
    if (!blob || !pixels) goto done;
    if (fread(blob, 1, (size_t)length, fp) != (size_t)length) goto done;
    FojAtlasRgba8Info info = {0};
    const int accepted = foj_atlas_dds_decode(
        blob, (size_t)length, pixels, FOJ_ATLAS_MAX_BYTES, &info);
    puts(accepted ? "1" : "0");
    code = 0;
done:
    free(pixels);
    free(blob);
    fclose(fp);
    return code;
}

#include "coll_grid.h"

#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

enum { FIELDS_MAX = 8, FIELD_CHARS = 80, LINE_CHARS = 640 };

static FojCollStatus fields_from_line(
    const char *line, size_t length, char fields[FIELDS_MAX][FIELD_CHARS],
    unsigned *count
) {
    if (length > LINE_CHARS || !line || !count) return FOJ_COLL_LIMIT;
    while (length && isspace((unsigned char)line[length - 1])) --length;
    if (length && line[length - 1] == ',') --length; /* observed trailing comma */
    unsigned n = 0;
    size_t start = 0;
    for (size_t i = 0; i <= length; ++i) {
        if (i != length && line[i] != ',') continue;
        if (n >= FIELDS_MAX) return FOJ_COLL_FORMAT;
        size_t begin = start, end = i;
        while (begin < end && isspace((unsigned char)line[begin])) ++begin;
        while (end > begin && isspace((unsigned char)line[end - 1])) --end;
        if (end == begin || end - begin >= FIELD_CHARS)
            return FOJ_COLL_FORMAT;
        memcpy(fields[n], line + begin, end - begin);
        fields[n][end - begin] = '\0';
        ++n;
        start = i + 1;
    }
    *count = n;
    return FOJ_COLL_OK;
}

static int parse_number(const char *text, float *number) {
    char *after = NULL;
    errno = 0;
    float value = strtof(text, &after);
    if (errno == ERANGE || after == text || *after || !isfinite(value))
        return 0;
    *number = value;
    return 1;
}

static int parse_integer(const char *text, int *number) {
    char *after = NULL;
    errno = 0;
    long value = strtol(text, &after, 10);
    if (errno || after == text || *after || value < -2147483647L ||
        value > 2147483647L) return 0;
    *number = (int)value;
    return 1;
}

static int parse_boolean(const char *text, uint8_t *flag) {
    if (strcmp(text, "true") == 0) { *flag = 1; return 1; }
    if (strcmp(text, "false") == 0) { *flag = 0; return 1; }
    return 0;
}

FojCollStatus foj_coll_parse(const char *data, size_t length, FojCollGrid *out) {
    if (!data || !out) return FOJ_COLL_ARGUMENT;
    if (length == 0 || length > FOJ_COLL_MAX_FILE_BYTES)
        return FOJ_COLL_LIMIT;

    memset(out, 0, sizeof(*out));
    size_t position = 0;
    unsigned row_number = 0;
    while (position < length) {
        size_t end = position;
        while (end < length && data[end] != '\n') {
            if (data[end] == '\0') return FOJ_COLL_FORMAT;
            if (end - position > LINE_CHARS) return FOJ_COLL_LIMIT;
            ++end;
        }
        char fields[FIELDS_MAX][FIELD_CHARS];
        unsigned count = 0;
        FojCollStatus result = fields_from_line(
            data + position, end - position, fields, &count
        );
        if (result != FOJ_COLL_OK) return result;
        position = end == length ? end : end + 1;
        if (row_number == 0) {
            if (count != 6 ||
                !parse_integer(fields[0], &out->width) ||
                !parse_integer(fields[1], &out->height)) return FOJ_COLL_FORMAT;
            if (out->width < 1 || out->height < 1 ||
                out->width > FOJ_COLL_MAX_SIDE ||
                out->height > FOJ_COLL_MAX_SIDE) return FOJ_COLL_DIMENSIONS;
            for (int n = 0; n < 2; ++n) {
                if (!parse_number(fields[2 + n], &out->origin[n]) ||
                    !parse_number(fields[4 + n], &out->step[n]) ||
                    out->step[n] == 0.0f) return FOJ_COLL_FORMAT;
            }
        } else {
            if (row_number > (unsigned)(out->width * out->height))
                return FOJ_COLL_COUNT;
            if (count != 8) return FOJ_COLL_FORMAT;
            int x = 0, y = 0, index = (int)row_number - 1;
            if (!parse_integer(fields[0], &x) ||
                !parse_integer(fields[1], &y) ||
                x != index % out->width || y != index / out->width)
                return FOJ_COLL_COORDINATES;
            for (int n = 0; n < 4; ++n)
                if (!parse_number(fields[2 + n], &out->samples[y][x][n]))
                    return FOJ_COLL_FORMAT;
            for (int n = 0; n < 2; ++n)
                if (!parse_boolean(fields[6 + n], &out->flags[y][x][n]))
                    return FOJ_COLL_FORMAT;
        }
        ++row_number;
    }
    if (row_number != (unsigned)(1 + out->width * out->height))
        return FOJ_COLL_COUNT;
    return FOJ_COLL_OK;
}

const char *foj_coll_error(FojCollStatus status) {
    switch (status) {
        case FOJ_COLL_OK: return "OK";
        case FOJ_COLL_ARGUMENT: return "Invalid argument";
        case FOJ_COLL_LIMIT: return "Input exceeds size limits";
        case FOJ_COLL_FORMAT: return "Malformed collision data";
        case FOJ_COLL_DIMENSIONS: return "Grid dimensions unsupported";
        case FOJ_COLL_COORDINATES: return "Cell coordinate/order mismatch";
        case FOJ_COLL_COUNT: return "Wrong number of collision cells";
        default: return "Unknown error";
    }
}

/* Stage239: deterministic host timing of the generated-only movement forecast.
 * Not a Nintendo Switch FPS benchmark; no PS3 AI/rules/assets measured.
 * Capture elapsed monotonic time without hardcoded performance thresholds.
 */
#define _POSIX_C_SOURCE 200809L
#include "tactical_battle.h"

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

enum { TRIALS = 5, GRID_PASSES = 8, CALLS = FOJ_TILE_COUNT * GRID_PASSES };
static volatile uint64_t consumed_digest;

typedef struct {
    uint64_t duration_ns;
    uint64_t digest;
    uint32_t calculations;
    uint32_t hits;
} Sample;

static void die(const char *reason) {
    fprintf(stderr, "Stage239 benchmark failed: %s\n", reason);
    exit(EXIT_FAILURE);
}

static uint64_t monotonic_ns(void) {
    struct timespec stamp;
    if (clock_gettime(CLOCK_MONOTONIC, &stamp) != 0)
        die("clock_gettime(CLOCK_MONOTONIC)");
    return (uint64_t)stamp.tv_sec * UINT64_C(1000000000) +
           (uint64_t)stamp.tv_nsec;
}

static uint64_t add_digest(uint64_t digest, const FojBattleThreatPreview *p,
                           int x, int y) {
    /* Same readout for both strategies; depend on an actual preview result.
     * Prevent removing the repeated baseline calls as dead work. */
    const uint64_t value =
        (uint64_t)p->can_move[y][x] |
        ((uint64_t)p->incoming_damage[y][x] << 8) |
        ((uint64_t)p->enemy_x_after[y][x] << 16) |
        ((uint64_t)p->enemy_y_after[y][x] << 24);
    return (digest ^ (value + UINT64_C(0x9e3779b97f4a7c15))) *
           UINT64_C(0x100000001b3);
}

static Sample measure(bool use_cache) {
    FojBattle battle;
    FojBattleThreatCache cache;
    FojBattleThreatPreview preview;
    foj_battle_init(&battle);
    foj_battle_threat_cache_init(&cache);
    if (foj_battle_confirm(&battle) != FOJ_BATTLE_SELECTED)
        die("the synthetic hero must be selected");
    const FojBattle before = battle;
    Sample result = {0};
    uint64_t digest = UINT64_C(0xcbf29ce484222325);
    const uint64_t start = monotonic_ns();
    for (int pass = 0; pass < GRID_PASSES; ++pass) {
        for (int y = 0; y < FOJ_HEIGHT; ++y) {
            for (int x = 0; x < FOJ_WIDTH; ++x) {
                battle.map.cursor_x = x;
                battle.map.cursor_y = y;
                bool ok = use_cache ?
                    foj_battle_preview_movement_threat_cached(
                        &cache, &battle, &preview) :
                    foj_battle_preview_movement_threat(&battle, &preview);
                if (!ok) die("forecast unexpectedly failed");
                digest = add_digest(digest, &preview, x, y);
            }
        }
    }
    const uint64_t end = monotonic_ns();
    if (end <= start) die("nonpositive monotonic duration");
    result.duration_ns = end - start;
    result.digest = digest;
    result.calculations = use_cache ? cache.calculations : (uint32_t)CALLS;
    result.hits = use_cache ? cache.hits : 0;
    if (use_cache &&
        (!cache.valid || cache.calculations != 1 ||
         cache.hits != (uint32_t)(CALLS - 1)))
        die("cursor sweep did not reuse exactly one risk matrix");
    if (memcmp(&battle, &before, sizeof(battle)) == 0)
        die("cursor sweep did not exercise the battlefield state");
    /* Only cursor must differ from initial state, no combat mutations. */
    battle.map.cursor_x = before.map.cursor_x;
    battle.map.cursor_y = before.map.cursor_y;
    if (memcmp(&battle, &before, sizeof(battle)) != 0)
        die("timed preview modified combat state");
    consumed_digest |= digest;
    return result;
}

static uint64_t median(uint64_t raw[TRIALS]) {
    uint64_t sorted[TRIALS];
    memcpy(sorted, raw, sizeof(sorted));
    for (int i = 1; i < TRIALS; ++i) {
        const uint64_t current = sorted[i];
        int j = i - 1;
        while (j >= 0 && sorted[j] > current) {
            sorted[j + 1] = sorted[j];
            --j;
        }
        sorted[j + 1] = current;
    }
    return sorted[TRIALS / 2];
}

static void write_samples(FILE *out, const uint64_t values[TRIALS]) {
    fputc('[', out);
    for (int i=0; i<TRIALS; ++i)
        fprintf(out, "%s%" PRIu64, i ? ", " : "", values[i]);
    fputc(']', out);
}

int main(int argc, char **argv) {
    if (argc != 3 || strcmp(argv[1], "--report") != 0) {
        fputs("usage: test_battle_threat_cost --report path.json\n", stderr);
        return EXIT_FAILURE;
    }

    uint64_t baseline[TRIALS], cached[TRIALS];
    uint64_t digest = 0;
    /* Warm up both code paths before taking trial medians. */
    const Sample warm_plain = measure(false);
    const Sample warm_cached = measure(true);
    if (warm_plain.digest != warm_cached.digest)
        die("warmup output mismatch");

    for (int i = 0; i < TRIALS; ++i) {
        Sample plain, fast;
        if ((i & 1) == 0) {
            plain = measure(false);
            fast = measure(true);
        } else {
            fast = measure(true);
            plain = measure(false);
        }
        if (plain.digest != fast.digest ||
            plain.digest != warm_plain.digest)
            die("uncached/cached data checksum diverged");
        if (plain.calculations != CALLS || plain.hits != 0 ||
            fast.calculations != 1 || fast.hits != CALLS - 1)
            die("forecast invocation counts incorrect");
        baseline[i] = plain.duration_ns;
        cached[i] = fast.duration_ns;
        digest = plain.digest;
    }

    const uint64_t baseline_mid = median(baseline);
    const uint64_t cached_mid = median(cached);
    if (baseline_mid == 0 || cached_mid == 0 || consumed_digest == 0)
        die("missing benchmark measurements");

    FILE *out = fopen(argv[2], "wx");
    if (!out) {
        perror("Stage239 report");
        return EXIT_FAILURE;
    }
    fprintf(out,
        "{\n"
        "  \"schema\": \"foj-stage239-host-threat-cost-v1\",\n"
        "  \"source\": \"generated-research-tactical-simulation\",\n"
        "  \"timing_source\": \"CLOCK_MONOTONIC\",\n"
        "  \"platform\": \"CI Linux host; not Switch or NeXium\",\n"
        "  \"original_ps3_assets_used\": false,\n"
        "  \"original_foj_ai_verified\": false,\n"
        "  \"switch_fps_measured\": false,\n"
        "  \"host_wall_time_not_cpu_cycles\": true,\n"
        "  \"grid_width\": %d,\n"
        "  \"grid_height\": %d,\n"
        "  \"cursor_passes\": %d,\n"
        "  \"calls_per_trial\": %d,\n"
        "  \"trials\": %d,\n"
        "  \"baseline_forecast_computations\": %d,\n"
        "  \"cached_forecast_computations\": 1,\n"
        "  \"cached_hits\": %d,\n"
        "  \"digests_identical\": true,\n"
        "  \"digest\": \"%016" PRIx64 "\",\n"
        "  \"baseline_duration_ns\": ",
        FOJ_WIDTH, FOJ_HEIGHT, GRID_PASSES, CALLS, TRIALS,
        CALLS, CALLS-1, digest);
    write_samples(out, baseline);
    fprintf(out, ",\n  \"cached_duration_ns\": ");
    write_samples(out, cached);
    fprintf(out,
        ",\n"
        "  \"baseline_median_ns\": %" PRIu64 ",\n"
        "  \"cached_median_ns\": %" PRIu64 ",\n"
        "  \"baseline_median_ns_per_call\": %.3f,\n"
        "  \"cached_median_ns_per_call\": %.3f,\n"
        "  \"observed_host_wall_time_ratio\": %.3f,\n"
        "  \"hard_performance_pass_threshold\": false\n"
        "}\n",
        baseline_mid, cached_mid,
        (double)baseline_mid / (double)CALLS,
        (double)cached_mid / (double)CALLS,
        (double)baseline_mid / (double)cached_mid);
    if (fclose(out) != 0) die("failed to write timing report");
    printf("Stage239 host timing: %d calls/trial, %d trials; "
           "plain median %.3f us/call, cached median %.3f us/call, "
           "ratio %.3f; all forecast digests match\n",
           CALLS, TRIALS,
           (double)baseline_mid/(double)CALLS/1000.0,
           (double)cached_mid/(double)CALLS/1000.0,
           (double)baseline_mid/(double)cached_mid);
    return EXIT_SUCCESS;
}

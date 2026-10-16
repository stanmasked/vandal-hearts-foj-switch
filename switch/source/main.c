/*
 * Vandal Hearts: Flames of Judgment — Nintendo Switch research bring-up.
 *
 * This is a standalone input/console smoke test, NOT the original game.
 * No Konami/PS3 code or commercial game data is included.
 */
#include <switch.h>
#include <stdio.h>

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    printf("Vandal Hearts: Flames of Judgment\n");
    printf("Nintendo Switch research prototype\n");
    printf("-----------------------------------\n");
    printf("Synthetic input smoke test only.\n");
    printf("Original PS3 game NOT running.\n\n");
    printf("A: confirm input    B: cancel input\n");
    printf("PLUS: exit homebrew\n\n");

    unsigned long a_count = 0;
    unsigned long b_count = 0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);

        if (pressed & HidNpadButton_Plus)
            break;
        if (pressed & HidNpadButton_A) {
            ++a_count;
            printf("A pressed (%lu)\n", a_count);
        }
        if (pressed & HidNpadButton_B) {
            ++b_count;
            printf("B pressed (%lu)\n", b_count);
        }

        consoleUpdate(NULL);
    }
    consoleExit(NULL);
    return 0;
}

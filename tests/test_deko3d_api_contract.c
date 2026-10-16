/* This host-only check includes the mock for local compile verification;
 * the real NRO independently compiles the same contract with real deko3d.
 */
#include <deko3d.h>
#include "deko3d_api_contract.h"
#include <stdio.h>

int main(void) {
    puts("deko3d ABI constants: verified against pinned upstream values");
    return 0;
}

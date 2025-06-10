#ifndef DEBUG_H
#define DEBUG_H

// NOLINTBEGIN
#include "vpi_user.h"

// Uncomment the following line to enable debug output
// #define DEBUG

#ifdef DEBUG
#define DBG(...)                                                                                                                                                                                       \
    do {                                                                                                                                                                                               \
        vpi_printf("[DBG] %s:%d:%s(): ", __FILE__, __LINE__, __func__);                                                                                                                                \
        vpi_printf(__VA_ARGS__);                                                                                                                                                                       \
        vpi_printf("\n");                                                                                                                                                                              \
    } while (0)
#else
#define DBG(...) ((void)0)
#endif

#define ERROR(...)                                                                                                                                                                                     \
    do {                                                                                                                                                                                               \
        vpi_printf("** Error: %s:%d:%s(): ", __FILE__, __LINE__, __func__);                                                                                                                            \
        vpi_printf(__VA_ARGS__);                                                                                                                                                                       \
        vpi_printf("\n");                                                                                                                                                                              \
    } while (0)

#define INFO(...)                                                                                                                                                                                      \
    do {                                                                                                                                                                                               \
        vpi_printf("** Info: ");                                                                                                                                                                       \
        vpi_printf(__VA_ARGS__);                                                                                                                                                                       \
        vpi_printf("\n");                                                                                                                                                                              \
    } while (0)
// NOLINTEND

#endif // DEBUG_H 
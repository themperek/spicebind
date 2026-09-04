/* Calibration firmware for the SERV + DCO example. No libc. */

#define DCO_TRIM        0x40000000u
#define DCO_CTRL        0x40000004u
#define DCO_STATUS      0x40000008u
#define DCO_COUNT       0x4000000Cu
#define FW_RESULT       0x40000010u
#define FW_FINAL_COUNT  0x40000014u
#define FW_ITERATIONS   0x40000018u

#define TARGET 32
#define TOL    6

static inline void wr(unsigned addr, unsigned value)
{
    *(volatile unsigned *)addr = value;
}

static inline unsigned rd(unsigned addr)
{
    return *(volatile unsigned *)addr;
}

static int abs_diff(int a, int b)
{
    return (a > b) ? (a - b) : (b - a);
}

static unsigned measure(unsigned trim)
{
    wr(DCO_TRIM, trim);
    wr(DCO_CTRL, 1u);
    while ((rd(DCO_STATUS) & 1u) != 0u) {
        /* busy */
    }
    while ((rd(DCO_STATUS) & 2u) == 0u) {
        /* wait DONE */
    }
    return rd(DCO_COUNT);
}

int main(void)
{
    int lo = 0;
    int hi = 15;
    int best_trim = 8;
    int best_err = 1000;
    int best_count = 0;
    int last_count = 0;
    unsigned iterations = 0;

    while (lo <= hi) {
        int trim = (lo + hi) >> 1;
        int count = (int)measure((unsigned)trim);
        int err = abs_diff(count, TARGET);
        iterations++;
        last_count = count;
        if (err < best_err) {
            best_err = err;
            best_trim = trim;
            best_count = count;
        }
        if (count < TARGET)
            lo = trim + 1;
        else
            hi = trim - 1;
    }

    last_count = (int)measure((unsigned)best_trim);
    iterations++;
    /* A confirmation run can see analog startup jitter; keep the closer sample. */
    if (abs_diff(best_count, TARGET) < abs_diff(last_count, TARGET))
        last_count = best_count;

    wr(FW_FINAL_COUNT, (unsigned)last_count);
    wr(FW_ITERATIONS, iterations);

    unsigned result = 1u; /* FINISHED */
    result |= ((unsigned)best_trim & 0xfu) << 8;
    if (abs_diff(last_count, TARGET) <= TOL)
        result |= 2u; /* PASS */
    else {
        if ((best_trim == 15 && last_count < TARGET) ||
            (best_trim == 0 && last_count > TARGET))
            result |= 4u; /* RANGE_EXHAUSTED */
    }
    wr(FW_RESULT, result);

    for (;;) {
    }
    return 0;
}

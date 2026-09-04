    .section .text.start, "ax"
    .option norvc
    .option norelax
    .global _start
    .extern main
    .extern _stack_top

_start:
    lui     sp, %hi(_stack_top)
    addi    sp, sp, %lo(_stack_top)
    jal     ra, main
1:
    j       1b

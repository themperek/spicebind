OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    ram (rwx) : ORIGIN = 0x00000000, LENGTH = 8K
}

SECTIONS
{
    .text : {
        *(.text.start)
        *(.text*)
    } > ram

    .rodata : { *(.rodata*) } > ram
    .data : { *(.data*) } > ram
    .bss : {
        *(.bss*)
        *(COMMON)
    } > ram

    _stack_top = ORIGIN(ram) + LENGTH(ram);
}

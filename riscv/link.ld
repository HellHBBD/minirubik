OUTPUT_ARCH(riscv)
ENTRY(_start)

PHDRS
{
    image PT_LOAD FLAGS(5);
    storage PT_LOAD FLAGS(6);
}

SECTIONS
{
    /* Ripes initializes non-alloc ELF sections at their stated addresses.
     * Keep the loadable image away from metadata located at address zero.
     */
    . = 0x1000;
    .text : ALIGN(4)
    {
        KEEP(*(.text.entry))
        *(.text .text.*)
    } :image

    .rodata : ALIGN(16)
    {
        *(.rodata .rodata.*)
    } :image

    .data : ALIGN(16)
    {
        *(.data .data.*)
    } :storage

    .bss (NOLOAD) : ALIGN(16)
    {
        *(.bss .bss.*)
    } :storage

    .riscv.attributes 0 : { *(.riscv.attributes) }
    /DISCARD/ : { *(.comment) *(.note.GNU-stack) }

    ASSERT(SIZEOF(.rodata) + SIZEOF(.data) + SIZEOF(.bss) <= 128 * 1024,
           "RV32I static data exceeds 128 KiB")
}

/* ZIRH - riscv-arch-test target model (H46)
 *
 * The core under test is the same serv_rf_top the chip integrates
 * (WITH_CSR=1 here so the suite's trap machinery runs; the chip's
 * CSR-less config is a documented area choice, not a different core).
 * Halt protocol: the test writes begin/end signature addresses and a
 * go flag to the magic window at 0x20000; tb_arch dumps the range and
 * finishes. */
#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                            \
        .align 8; .global tohost; tohost: .dword 0;                     \
        .align 8; .global fromhost; fromhost: .dword 0;                 \
        .popsection;                                                    \
        .align 8; .global begin_regstate; begin_regstate:               \
        .word 128;                                                      \
        .align 8; .global end_regstate; end_regstate:                   \
        .word 4;

#define RVMODEL_HALT                                                    \
        la   t0, begin_signature;                                       \
        li   t1, 0x200000;                                               \
        sw   t0, 0(t1);                                                 \
        la   t0, end_signature;                                         \
        sw   t0, 4(t1);                                                 \
        li   t0, 1;                                                     \
        sw   t0, 8(t1);                                                 \
        self_loop: j self_loop;

#define RVMODEL_BOOT

#define RVMODEL_DATA_BEGIN                                              \
        .align 4; .global begin_signature; begin_signature:

#define RVMODEL_DATA_END                                                \
        .align 4; .global end_signature; end_signature:                 \
        RVMODEL_DATA_SECTION

#define RVMODEL_IO_INIT
#define RVMODEL_IO_WRITE_STR(_R, _STR)
#define RVMODEL_IO_CHECK()
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)
#define RVMODEL_SET_MSW_INT
#define RVMODEL_CLEAR_MSW_INT
#define RVMODEL_CLEAR_MTIMER_INT
#define RVMODEL_CLEAR_MEXT_INT

#endif

"""Adds the PPC/VMX128 instructions our games need to XenonRecomp and fixes what it gets wrong.

Idempotent: run against a pristine recompiler.cpp (keeps a .orig backup).
usage: patch_recompiler.py <path to XenonRecomp/XenonRecomp/recompiler.cpp>
"""
import os
import shutil
import sys

NEW_CASES = r'''
    // ---- DAO additions: instructions XenonRecomp lacked ----

    // D-form loads/stores with update: operands { rT, D, rA }
    case PPC_INST_LHZU:
    case PPC_INST_LHAU:
    case PPC_INST_STHU:
    case PPC_INST_LFSU:
    case PPC_INST_LFDU:
    case PPC_INST_STFSU:
    case PPC_INST_STFDU:
        println("\t{} = {} + {}.u32;", ea(), int32_t(insn.operands[1]), r(insn.operands[2]));
        switch (insn.opcode->id)
        {
        case PPC_INST_LHZU: println("\t{}.u64 = PPC_LOAD_U16({});", r(insn.operands[0]), ea()); break;
        case PPC_INST_LHAU: println("\t{}.s64 = int16_t(PPC_LOAD_U16({}));", r(insn.operands[0]), ea()); break;
        case PPC_INST_STHU: println("\tPPC_STORE_U16({}, {}.u16);", ea(), r(insn.operands[0])); break;
        case PPC_INST_LFSU:
            printSetFlushMode(false);
            println("\t{}.u32 = PPC_LOAD_U32({});", temp(), ea());
            println("\t{}.f64 = double({}.f32);", f(insn.operands[0]), temp());
            break;
        case PPC_INST_LFDU:
            printSetFlushMode(false);
            println("\t{}.u64 = PPC_LOAD_U64({});", f(insn.operands[0]), ea());
            break;
        case PPC_INST_STFSU:
            printSetFlushMode(false);
            println("\t{}.f32 = float({}.f64);", temp(), f(insn.operands[0]));
            println("\tPPC_STORE_U32({}, {}.u32);", ea(), temp());
            break;
        case PPC_INST_STFDU:
            printSetFlushMode(false);
            println("\tPPC_STORE_U64({}, {}.u64);", ea(), f(insn.operands[0]));
            break;
        }
        println("\t{}.u32 = {};", r(insn.operands[2]), ea());
        break;

    // X-form loads/stores with update: operands { rT, rA, rB }
    case PPC_INST_LBZUX:
    case PPC_INST_LHZUX:
    case PPC_INST_LWZUX:
    case PPC_INST_LWAUX:
    case PPC_INST_LFSUX:
    case PPC_INST_LFDUX:
    case PPC_INST_STBUX:
    case PPC_INST_STHUX:
    case PPC_INST_STDUX:
    case PPC_INST_STFSUX:
        println("\t{} = {}.u32 + {}.u32;", ea(), r(insn.operands[1]), r(insn.operands[2]));
        switch (insn.opcode->id)
        {
        case PPC_INST_LBZUX: println("\t{}.u64 = PPC_LOAD_U8({});", r(insn.operands[0]), ea()); break;
        case PPC_INST_LHZUX: println("\t{}.u64 = PPC_LOAD_U16({});", r(insn.operands[0]), ea()); break;
        case PPC_INST_LWZUX: println("\t{}.u64 = PPC_LOAD_U32({});", r(insn.operands[0]), ea()); break;
        case PPC_INST_LWAUX: println("\t{}.s64 = int32_t(PPC_LOAD_U32({}));", r(insn.operands[0]), ea()); break;
        case PPC_INST_LFSUX:
            printSetFlushMode(false);
            println("\t{}.u32 = PPC_LOAD_U32({});", temp(), ea());
            println("\t{}.f64 = double({}.f32);", f(insn.operands[0]), temp());
            break;
        case PPC_INST_LFDUX:
            printSetFlushMode(false);
            println("\t{}.u64 = PPC_LOAD_U64({});", f(insn.operands[0]), ea());
            break;
        case PPC_INST_STBUX: println("\tPPC_STORE_U8({}, {}.u8);", ea(), r(insn.operands[0])); break;
        case PPC_INST_STHUX: println("\tPPC_STORE_U16({}, {}.u16);", ea(), r(insn.operands[0])); break;
        case PPC_INST_STDUX: println("\tPPC_STORE_U64({}, {}.u64);", ea(), r(insn.operands[0])); break;
        case PPC_INST_STFSUX:
            printSetFlushMode(false);
            println("\t{}.f32 = float({}.f64);", temp(), f(insn.operands[0]));
            println("\tPPC_STORE_U32({}, {}.u32);", ea(), temp());
            break;
        }
        println("\t{}.u32 = {};", r(insn.operands[1]), ea());
        break;

    case PPC_INST_EQV:
        println("\t{}.u64 = ~({}.u64 ^ {}.u64);", r(insn.operands[0]), r(insn.operands[1]), r(insn.operands[2]));
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.compare<int32_t>({}.s32, 0, {});", cr(0), r(insn.operands[0]), xer());
        break;

    case PPC_INST_ADDC:
        println("\t{}.ca = {}.u32 + {}.u32 < {}.u32;", xer(), r(insn.operands[1]), r(insn.operands[2]), r(insn.operands[1]));
        println("\t{}.u64 = {}.u64 + {}.u64;", r(insn.operands[0]), r(insn.operands[1]), r(insn.operands[2]));
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.compare<int32_t>({}.s32, 0, {});", cr(0), r(insn.operands[0]), xer());
        break;

    case PPC_INST_ADDME:
        // rD = rA + CA - 1; carry out unless rA == 0 && CA == 0
        println("\t{}.u8 = ({}.u32 != 0) | {}.ca;", temp(), r(insn.operands[1]), xer());
        println("\t{}.u64 = {}.u64 + {}.ca - 1;", r(insn.operands[0]), r(insn.operands[1]), xer());
        println("\t{}.ca = {}.u8;", xer(), temp());
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.compare<int32_t>({}.s32, 0, {});", cr(0), r(insn.operands[0]), xer());
        break;

    case PPC_INST_SUBFZE:
        // rD = ~rA + CA; carry out only when ~rA == 0xFFFFFFFF and CA == 1
        println("\t{}.u8 = ({}.u32 == 0) & {}.ca;", temp(), r(insn.operands[1]), xer());
        println("\t{}.u64 = ~{}.u64 + {}.ca;", r(insn.operands[0]), r(insn.operands[1]), xer());
        println("\t{}.ca = {}.u8;", xer(), temp());
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.compare<int32_t>({}.s32, 0, {});", cr(0), r(insn.operands[0]), xer());
        break;

    case PPC_INST_BDZF:
    case PPC_INST_BDNZT:
    {
        // operands { BI, target }; BI selects lt/gt/eq/so of cr[BI / 4]
        static constexpr const char* bits[] = { "lt", "gt", "eq", "so" };
        const bool zero = insn.opcode->id == PPC_INST_BDZF;
        const bool want = insn.opcode->id == PPC_INST_BDNZT;
        println("\t--{}.u64;", ctr());
        const auto cond = fmt::format("{}.u32 {} 0 && {}{}.{}", ctr(), zero ? "==" : "!=", want ? "" : "!", cr(insn.operands[0] / 4), bits[insn.operands[0] % 4]);
        if (insn.operands[1] < fn.base || insn.operands[1] >= fn.base + fn.size)
        {
            println("\tif ({}) {{", cond);
            print("\t");
            printFunctionCall(insn.operands[1]);
            println("\t\treturn;");
            println("\t}}");
        }
        else
        {
            println("\tif ({}) goto loc_{:X};", cond, insn.operands[1]);
        }
        break;
    }

    case PPC_INST_BSO:
        printConditionalBranch(false, "so");
        break;

    case PPC_INST_BNS:
        printConditionalBranch(true, "so");
        break;

    case PPC_INST_BSOLR:
        println("\tif ({}.so) return;", cr(insn.operands[0]));
        break;

    case PPC_INST_FRSQRTE:
        printSetFlushMode(false);
        println("\t{}.f64 = 1.0 / sqrt({}.f64);", f(insn.operands[0]), f(insn.operands[1]));
        break;

    case PPC_INST_DCBST:
        // no op
        break;

    case PPC_INST_LVEHX:
        // like lvewx: load the containing aligned vector (element position is preserved)
        print("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(base + ((", v(insn.operands[0]));
        if (insn.operands[1] != 0)
            print("{}.u32 + ", r(insn.operands[1]));
        println("{}.u32) & ~0xF))), simde_mm_load_si128((simde__m128i*)VectorMaskL)));", r(insn.operands[2]));
        break;

    case PPC_INST_VNOR128:
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_xor_si128(simde_mm_or_si128(simde_mm_load_si128((simde__m128i*){}.u8), simde_mm_load_si128((simde__m128i*){}.u8)), simde_mm_set1_epi32(-1)));", v(insn.operands[0]), v(insn.operands[1]), v(insn.operands[2]));
        break;

    case PPC_INST_VSEL128:
        // operands { vD, vA, vB, vD }: vD = (vA & ~vD) | (vB & vD)
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_or_si128(simde_mm_andnot_si128(simde_mm_load_si128((simde__m128i*){}.u8), simde_mm_load_si128((simde__m128i*){}.u8)), simde_mm_and_si128(simde_mm_load_si128((simde__m128i*){}.u8), simde_mm_load_si128((simde__m128i*){}.u8))));", v(insn.operands[0]), v(insn.operands[3]), v(insn.operands[1]), v(insn.operands[3]), v(insn.operands[2]));
        break;

    case PPC_INST_VPKSWSS:
    case PPC_INST_VPKSWSS128:
        // vectors are stored reversed, so the high (vA) half goes second
        println("\tsimde_mm_store_si128((simde__m128i*){}.s16, simde_mm_packs_epi32(simde_mm_load_si128((simde__m128i*){}.s32), simde_mm_load_si128((simde__m128i*){}.s32)));", v(insn.operands[0]), v(insn.operands[2]), v(insn.operands[1]));
        break;

    case PPC_INST_VSUBSHS:
        println("\tsimde_mm_store_si128((simde__m128i*){}.s16, simde_mm_subs_epi16(simde_mm_load_si128((simde__m128i*){}.s16), simde_mm_load_si128((simde__m128i*){}.s16)));", v(insn.operands[0]), v(insn.operands[1]), v(insn.operands[2]));
        break;

    case PPC_INST_VADDSWS:
        for (size_t i = 0; i < 4; i++)
            println("\t{{ int64_t s = int64_t({}.s32[{}]) + {}.s32[{}]; {}.s32[{}] = int32_t(s > 0x7FFFFFFFll ? 0x7FFFFFFFll : (s < -0x80000000ll ? -0x80000000ll : s)); }}", v(insn.operands[1]), i, v(insn.operands[2]), i, vTemp(), i);
        println("\t{} = {};", v(insn.operands[0]), vTemp());
        break;

    case PPC_INST_VCFPUXWS128:
    {
        // float -> u32 with saturation, scaled by 2^uimm; NaN and negatives become 0
        printSetFlushMode(true);
        const float scale = ldexp(1.0f, int32_t(insn.operands[2]));
        for (size_t i = 0; i < 4; i++)
        {
            println("\t{{ float x = {}.f32[{}] * float({});{}.u32[{}] = !(x > 0.0f) ? 0u : (x >= 4294967296.0f ? 0xFFFFFFFFu : uint32_t(x)); }}",
                v(insn.operands[1]), i, scale, vTemp(), i);
        }
        println("\t{} = {};", v(insn.operands[0]), vTemp());
        break;
    }

    case PPC_INST_VCMPBFP:
    case PPC_INST_VCMPBFP128:
        // bounds compare: bit31 = !(a <= b), bit30 = !(a >= -b); NaN sets both
        printSetFlushMode(true);
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_or_si128("
            "simde_mm_andnot_si128(simde_mm_castps_si128(simde_mm_cmple_ps(simde_mm_load_ps({}.f32), simde_mm_load_ps({}.f32))), simde_mm_set1_epi32(int(0x80000000))), "
            "simde_mm_andnot_si128(simde_mm_castps_si128(simde_mm_cmpge_ps(simde_mm_load_ps({}.f32), simde_mm_xor_ps(simde_mm_load_ps({}.f32), simde_mm_castsi128_ps(simde_mm_set1_epi32(int(0x80000000)))))), simde_mm_set1_epi32(0x40000000))));",
            vTemp(), v(insn.operands[1]), v(insn.operands[2]), v(insn.operands[1]), v(insn.operands[2]));
        println("\t{} = {};", v(insn.operands[0]), vTemp());
        if (strchr(insn.opcode->name, '.'))
        {
            println("\t{}.lt = 0; {}.gt = 0; {}.so = 0;", cr(6), cr(6), cr(6));
            println("\t{}.eq = simde_mm_movemask_epi8(simde_mm_cmpeq_epi32(simde_mm_load_si128((simde__m128i*){}.u8), simde_mm_setzero_si128())) == 0xFFFF;", cr(6), vTemp());
        }
        break;

    // From the State of Decay port. Semantics follow Xenia's PPC frontend (ppc_emit_*.cc). Vector registers are held
    // element-reversed (guest element i of a word vector is host u32[3 - i]).

    case PPC_INST_LDUX:
    case PPC_INST_STFDUX:
        println("\t{} = {}.u32 + {}.u32;", ea(), r(insn.operands[1]), r(insn.operands[2]));
        if (insn.opcode->id == PPC_INST_LDUX)
        {
            println("\t{}.u64 = PPC_LOAD_U64({});", r(insn.operands[0]), ea());
        }
        else
        {
            printSetFlushMode(false);
            println("\tPPC_STORE_U64({}, {}.u64);", ea(), f(insn.operands[0]));
        }
        println("\t{}.u32 = {};", r(insn.operands[1]), ea());
        break;

    case PPC_INST_LHBRX:
        print("\t{}.u64 = __builtin_bswap16(PPC_LOAD_U16(", r(insn.operands[0]));
        if (insn.operands[1] != 0)
            print("{}.u32 + ", r(insn.operands[1]));
        println("{}.u32));", r(insn.operands[2]));
        break;

    case PPC_INST_STVEBX:
        // NOTE: accounting for the full vector reversal here
        print("\t{} = ", ea());
        if (insn.operands[1] != 0)
            print("{}.u32 + ", r(insn.operands[1]));
        println("{}.u32;", r(insn.operands[2]));
        println("\tPPC_STORE_U8({}, {}.u8[15 - ({} & 0xF)]);", ea(), v(insn.operands[0]), ea());
        break;

    case PPC_INST_FCTIW:
        // Current rounding mode, saturating (PPCRoundToInt32 in ppc_context.h).
        printSetFlushMode(false);
        println("\t{}.s64 = PPCRoundToInt32({}.f64);", f(insn.operands[0]), f(insn.operands[1]));
        break;

    case PPC_INST_FNMADD:
        // As XenonRecomp's other multiply-adds: not fused.
        printSetFlushMode(false);
        println("\t{}.f64 = -({}.f64 * {}.f64 + {}.f64);", f(insn.operands[0]), f(insn.operands[1]), f(insn.operands[2]), f(insn.operands[3]));
        break;

    case PPC_INST_MULHD:
        println("\t{}.s64 = int64_t((__int128({}.s64) * __int128({}.s64)) >> 64);", r(insn.operands[0]), r(insn.operands[1]), r(insn.operands[2]));
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.compare<int64_t>({}.s64, 0, {});", cr(0), r(insn.operands[0]), xer());
        break;

    case PPC_INST_MULHDU:
        println("\t{}.u64 = uint64_t((static_cast<unsigned __int128>({}.u64) * static_cast<unsigned __int128>({}.u64)) >> 64);", r(insn.operands[0]), r(insn.operands[1]), r(insn.operands[2]));
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.compare<int64_t>({}.s64, 0, {});", cr(0), r(insn.operands[0]), xer());
        break;

    case PPC_INST_VMINSW:
        println("\tsimde_mm_store_si128((simde__m128i*){}.u32, simde_mm_min_epi32(simde_mm_load_si128((simde__m128i*){}.u32), simde_mm_load_si128((simde__m128i*){}.u32)));", v(insn.operands[0]), v(insn.operands[1]), v(insn.operands[2]));
        break;

    case PPC_INST_VSUBUWM:
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_sub_epi32(simde_mm_load_si128((simde__m128i*){}.u8), simde_mm_load_si128((simde__m128i*){}.u8)));", v(insn.operands[0]), v(insn.operands[1]), v(insn.operands[2]));
        break;

    case PPC_INST_VPKSHSS:
    case PPC_INST_VPKSHSS128:
        // vA's halfwords go to the guest's high half (host bytes 8-15), as in vpkshus.
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_packs_epi16(simde_mm_load_si128((simde__m128i*){}.s16), simde_mm_load_si128((simde__m128i*){}.s16)));", v(insn.operands[0]), v(insn.operands[2]), v(insn.operands[1]));
        break;

    case PPC_INST_VCMPGTUW:
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_cmpgt_epu32(simde_mm_load_si128((simde__m128i*){}.u32), simde_mm_load_si128((simde__m128i*){}.u32)));", v(insn.operands[0]), v(insn.operands[1]), v(insn.operands[2]));
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.setFromMask(simde_mm_load_ps({}.f32), 0xF);", cr(6), v(insn.operands[0]));
        break;

    case PPC_INST_VCMPGTSW:
        println("\tsimde_mm_store_si128((simde__m128i*){}.u8, simde_mm_cmpgt_epi32(simde_mm_load_si128((simde__m128i*){}.u32), simde_mm_load_si128((simde__m128i*){}.u32)));", v(insn.operands[0]), v(insn.operands[1]), v(insn.operands[2]));
        if (strchr(insn.opcode->name, '.'))
            println("\t{}.setFromMask(simde_mm_load_ps({}.f32), 0xF);", cr(6), v(insn.operands[0]));
        break;

    case PPC_INST_VAVGSW:
        // (a + b + 1) >> 1 without overflow
        for (size_t i = 0; i < 4; i++)
            println("\t{}.s32[{}] = int32_t((int64_t({}.s32[{}]) + int64_t({}.s32[{}]) + 1) >> 1);", v(insn.operands[0]), i, v(insn.operands[1]), i, v(insn.operands[2]), i);
        break;

    case PPC_INST_VSLH:
        for (size_t i = 0; i < 8; i++)
            println("\t{}.u16[{}] = {}.u16[{}] << ({}.u16[{}] & 0xF);", v(insn.operands[0]), i, v(insn.operands[1]), i, v(insn.operands[2]), i);
        break;

    case PPC_INST_VSRH:
        for (size_t i = 0; i < 8; i++)
            println("\t{}.u16[{}] = {}.u16[{}] >> ({}.u16[{}] & 0xF);", v(insn.operands[0]), i, v(insn.operands[1]), i, v(insn.operands[2]), i);
        break;

    case PPC_INST_VRLW128:
        for (size_t i = 0; i < 4; i++)
            println("\t{}.u32[{}] = __builtin_rotateleft32({}.u32[{}], {}.u32[{}] & 0x1F);", v(insn.operands[0]), i, v(insn.operands[1]), i, v(insn.operands[2]), i);
        break;

    case PPC_INST_VSL:
        // Whole-register shift left by vB's last byte & 7 bits. The reversed layout makes
        // the host's little-endian 128-bit value the guest's big-endian one.
        println("\t{}.u32 = {}.u8[0] & 0x7;", temp(), v(insn.operands[2]));
        println("\t{0}.u64[1] = ({1}.u64[1] << {2}.u32) | ({2}.u32 ? {1}.u64[0] >> (64 - {2}.u32) : 0);", vTemp(), v(insn.operands[1]), temp());
        println("\t{}.u64[0] = {}.u64[0] << {}.u32;", vTemp(), v(insn.operands[1]), temp());
        println("\t{} = {};", v(insn.operands[0]), vTemp());
        break;

    case PPC_INST_VSLO:
    case PPC_INST_VSLO128:
        // Whole-register shift left by (vB's last byte >> 3) & 0xF bytes.
        println("\t{}.u32 = ({}.u8[0] >> 3) & 0xF;", temp(), v(insn.operands[2]));
        println("\tfor (uint32_t i = 0; i < 16; i++) {}.u8[i] = i >= {}.u32 ? {}.u8[i - {}.u32] : 0;", vTemp(), temp(), v(insn.operands[1]), temp());
        println("\t{} = {};", v(insn.operands[0]), vTemp());
        break;

'''

OLD_VCMPBFP = '''    case PPC_INST_VCMPBFP:
    case PPC_INST_VCMPBFP128:
        println("\\t__builtin_debugtrap();");
        break;

'''

OLD_BDNZF = '''        // NOTE: assuming eq here as a shortcut because all the instructions in the game do that
        println("\\t--{}.u64;", ctr());
        println("\\tif ({}.u32 != 0 && !{}.eq) goto loc_{:X};", ctr(), cr(insn.operands[0] / 4), insn.operands[1]);'''

NEW_BDNZF = '''    {
        // BI selects lt/gt/eq/so of cr[BI / 4] (upstream assumed eq)
        static constexpr const char* bits[] = { "lt", "gt", "eq", "so" };
        println("\\t--{}.u64;", ctr());
        println("\\tif ({}.u32 != 0 && !{}.{}) goto loc_{:X};", ctr(), cr(insn.operands[0] / 4), bits[insn.operands[0] % 4], insn.operands[1]);
    }'''

ANCHOR = '    default:\n        return false;\n    }'

# mftb must tick at the 360's 49.875 MHz, not the host TSC rate.
OLD_MFTB = '''        println("\\t{}.u64 = __rdtsc();", r(insn.operands[0]));'''
NEW_MFTB = '''        println("\\t{}.u64 = PPC_QUERY_TIMEBASE();", r(insn.operands[0]));'''

# fctid/fctidz/fctiwz went through simde's SSE2 conversions, which on ARM64 (no native path)
# round ties away from zero whatever FPSCR[RN] says, give 0 for NaN and turn exactly INT32_MAX
# into INT32_MIN. These helpers follow the PowerPC definition on every host (found in the State
# of Decay port; 184 cases in the four FPSCR modes pass on x86-64, x86-64-v3 and the S25's ARM64).
OLD_FCTID = '''        println("\\t{}.s64 = ({}.f64 > double(LLONG_MAX)) ? LLONG_MAX : simde_mm_cvtsd_si64(simde_mm_load_sd(&{}.f64));", f(insn.operands[0]), f(insn.operands[1]), f(insn.operands[1]));'''
NEW_FCTID = '''        println("\\t{}.s64 = PPCRoundToInt64({}.f64);", f(insn.operands[0]), f(insn.operands[1]));'''
OLD_FCTIDZ = '''        println("\\t{}.s64 = ({}.f64 > double(LLONG_MAX)) ? LLONG_MAX : simde_mm_cvttsd_si64(simde_mm_load_sd(&{}.f64));", f(insn.operands[0]), f(insn.operands[1]), f(insn.operands[1]));'''
NEW_FCTIDZ = '''        println("\\t{}.s64 = PPCTruncToInt64({}.f64);", f(insn.operands[0]), f(insn.operands[1]));'''
OLD_FCTIWZ = '''        println("\\t{}.s64 = ({}.f64 > double(INT_MAX)) ? INT_MAX : simde_mm_cvttsd_si32(simde_mm_load_sd(&{}.f64));", f(insn.operands[0]), f(insn.operands[1]), f(insn.operands[1]));'''
NEW_FCTIWZ = '''        println("\\t{}.s64 = PPCTruncToInt32({}.f64);", f(insn.operands[0]), f(insn.operands[1]));'''

# Jump tables switch on the index's low 32 bits, as the guest bounds it (cmplwi) and indexes
# the table with it: with dirty upper bits the 360 takes the right case, while a 64-bit switch
# matched none and read clang's table out of range (State of Decay crashed this way; found
# there).
OLD_SWITCH = '''            println("\\tswitch ({}.u64) {{", r(switchTable->second.r));'''
NEW_SWITCH = '''            println("\\tswitch ({}.u32) {{", r(switchTable->second.r));'''

# The disassembler's default dialect includes PPC403/405, whose multiply-accumulate
# entries (opcode 4) come before the VMX128 ones in its table: State of Decay's three
# `vsldoi128 vD,vA,vB,12` words (VX128_5 form, bit 0x10 set) decoded as `mullhwu.`.
# Xenon has no 403/405 instructions; drop them from the "cell" (Xenon) dialect.
DIALECT_OLD = '''        dialect |= PPC_OPCODE_POWER4 | PPC_OPCODE_CELL | PPC_OPCODE_ALTIVEC | PPC_OPCODE_VMX_128;
'''
DIALECT_NEW = '''    {
        dialect |= PPC_OPCODE_POWER4 | PPC_OPCODE_CELL | PPC_OPCODE_ALTIVEC | PPC_OPCODE_VMX_128;
        dialect &= ~PPC_OPCODE_403; // Xenon: opcode 4 is VMX/VMX128, never 403/405 multiply-accumulate
    }
'''

# Record forms XenonRecomp ignored (it warned "RC bit enabled but no comparison").
RLWIMI_OLD = '''        println("\\t{}.u64 = (__builtin_rotateleft32({}.u32, {}) & 0x{:X}) | ({}.u64 & 0x{:X});", r(insn.operands[0]), r(insn.operands[1]), insn.operands[2], mask, r(insn.operands[0]), ~mask);
'''
RLWIMI_NEW = RLWIMI_OLD + '''        if (strchr(insn.opcode->name, '.'))
            println("\\t{}.compare<int32_t>({}.s32, 0, {});", cr(0), r(insn.operands[0]), xer());
'''
RLDICL_OLD = '''        println("\\t{}.u64 = __builtin_rotateleft64({}.u64, {}) & 0x{:X};", r(insn.operands[0]), r(insn.operands[1]), insn.operands[2], ComputeMask(insn.operands[3], 63));
'''
RLDICL_NEW = RLDICL_OLD + '''        if (strchr(insn.opcode->name, '.'))
            println("\\t{}.compare<int64_t>({}.s64, 0, {});", cr(0), r(insn.operands[0]), xer());
'''

# vupkd3d128: FLOAT16_2 (type 3) and FLOAT16_4 (type 5), after the existing NORMSHORT2.
# The packed data is in the guest's last word(s): FLOAT16_2 x = high half of word 3,
# y = low half, z = 0, w = 1; FLOAT16_4 x..w = halfwords 4..7 (host u16[3..0]).
UPK_OLD = '''            println("\\t{}.f32[1] = 0.0f;", vTemp());
            println("\\t{}.f32[0] = 1.0f;", vTemp());
            println("\\t{} = {};", v(insn.operands[0]), vTemp());
            break;
'''
UPK_NEW = UPK_OLD + '''
        case 3: // float16_2
            println("\\t{}.f32[3] = PPCHalfToFloat({}.u16[1]);", vTemp(), v(insn.operands[1]));
            println("\\t{}.f32[2] = PPCHalfToFloat({}.u16[0]);", vTemp(), v(insn.operands[1]));
            println("\\t{}.f32[1] = 0.0f;", vTemp());
            println("\\t{}.f32[0] = 1.0f;", vTemp());
            println("\\t{} = {};", v(insn.operands[0]), vTemp());
            break;

        case 5: // float16_4
            for (size_t i = 0; i < 4; i++)
                println("\\t{}.f32[{}] = PPCHalfToFloat({}.u16[{}]);", vTemp(), i, v(insn.operands[1]), i);
            println("\\t{} = {};", v(insn.operands[0]), vTemp());
            break;
'''

# vpkd3d128 FLOAT16_2 (type 3), packed into one word like D3DCOLOR (pack 1: word
# operands[4] counted from the host's end) with float16_4's conversion: x in the high half.
PK_OLD = '''        		println("\\t{}.u16[{}] |= (({}.u32[{}]&0x80000000)>>16);", v(insn.operands[0]), i+(2*insn.operands[4]), v(insn.operands[1]), i);
            }
            break;
'''
PK_NEW = PK_OLD + '''
        case 3: // float16_2
            if (insn.operands[3] != 1)
                fmt::println("Unexpected float16_2 pack instruction at {:X}", base);

            for (size_t i = 2; i < 4; i++)
            {
                println("\\t{}.u32 = ({}.u32[{}]&0x7FFFFFFF);", temp(), v(insn.operands[1]), i);
                println("\\t{0}.u8[0] = ({1}.f32 != {1}.f32) || ({1}.f32 > 65504.0f) ? 0xFF : (({2}.u32[{3}]&0x7f800000)>>23);", vTemp(), temp(), v(insn.operands[1]), i);
                println("\\t{}.u16 = {}.u8[0] != 0xFF ? (({}.u32[{}]&0x7FE000)>>13) : 0x0;", temp(), vTemp(), v(insn.operands[1]), i);
                println("\\t{0}.u16[{1}] = {2}.u8[0] != 0xFF ? ({2}.u8[0] > 0x70 ? ((({2}.u8[0]-0x70)<<10)+{3}.u16) : (0x71-{2}.u8[0] > 31 ? 0x0 : ((0x400+{3}.u16)>>(0x71-{2}.u8[0])))) : 0x7FFF;", v(insn.operands[0]), (i - 2) + (2 * insn.operands[4]), vTemp(), temp());
                println("\\t{}.u16[{}] |= (({}.u32[{}]&0x80000000)>>16);", v(insn.operands[0]), (i - 2) + (2 * insn.operands[4]), v(insn.operands[1]), i);
            }
            break;
'''


# blrl was a debug trap. State of Decay's one (0x83620FCC, the CRT helper that calls a C++ catch
# funclet: mtlr r3; blrl) becomes an indirect call through the old LR, as bctrl does.
BLRL_OLD = '''    case PPC_INST_BLRL:
        println("__builtin_debugtrap();");
        break;
'''
BLRL_NEW = '''    case PPC_INST_BLRL:
        println("\\t{}.u32 = ctx.lr;", temp());
        if (!config.skipLr)
            println("\\tctx.lr = 0x{:X};", base + 4);
        println("\\tPPC_CALL_INDIRECT_FUNC({}.u32);", temp());
        csrState = CSRState::Unknown; // the call could change it
        break;
'''

# ...which the runtime provides through this hook in the generated ppc_context.h.
CONTEXT_ANCHOR = '#define PPC_MEMORY_SIZE 0x100000000ull'
CONTEXT_ADDITION = '''#define PPC_MEMORY_SIZE 0x100000000ull

#ifndef PPC_QUERY_TIMEBASE
uint64_t PPCQueryTimebase() noexcept;
#define PPC_QUERY_TIMEBASE() PPCQueryTimebase()
#endif

// fctid/fctidz/fctiwz as PowerPC defines them: NaN gives the most negative value, out-of-range
// values saturate (checked before rounding: every double at or beyond 2^63 is an integer), the
// rest round in the current mode (FPSCR[RN], kept in MXCSR/FPCR) or truncate. The generated
// code is built with strict floating point, so the compiler doesn't assume the mode.
inline int64_t PPCRoundToInt64(double v) noexcept
{
    if (__builtin_isnan(v) || v < -9223372036854775808.0)
        return INT64_MIN;
    if (v >= 9223372036854775808.0)
        return INT64_MAX;
#if defined(__x86_64__) || defined(_M_X64)
    return simde_mm_cvtsd_si64(simde_mm_set_sd(v)); // cvtsd2si reads MXCSR
#else
    return int64_t(std::nearbyint(v)); // reads FPCR
#endif
}

inline int32_t PPCRoundToInt32(double v) noexcept
{
    if (__builtin_isnan(v))
        return INT32_MIN;
    int64_t r = PPCRoundToInt64(v); // exact below 2^63, saturated beyond
    return r > INT32_MAX ? INT32_MAX : r < INT32_MIN ? INT32_MIN : int32_t(r);
}

inline int64_t PPCTruncToInt64(double v) noexcept
{
    if (__builtin_isnan(v) || v < -9223372036854775808.0)
        return INT64_MIN;
    return v >= 9223372036854775808.0 ? INT64_MAX : int64_t(v);
}

inline int32_t PPCTruncToInt32(double v) noexcept
{
    if (__builtin_isnan(v) || v <= -2147483649.0)
        return INT32_MIN;
    return v >= 2147483648.0 ? INT32_MAX : int32_t(v);
}

inline simde__m128i simde_mm_cmpgt_epu32(simde__m128i a, simde__m128i b)
{
    simde__m128i c = simde_mm_set1_epi32(int(0x80000000));
    return simde_mm_cmpgt_epi32(simde_mm_xor_si128(a, c), simde_mm_xor_si128(b, c));
}

// IEEE 754 binary16 to float, as Xenia's vupkd3d128 FLOAT16 unpack (F16C): exponent 31
// is infinity/NaN, denormals are exact.
inline float PPCHalfToFloat(uint16_t h) noexcept
{
    uint32_t sign = uint32_t(h & 0x8000) << 16;
    uint32_t exponent = (h >> 10) & 0x1F;
    uint32_t mantissa = h & 0x3FF;
    uint32_t bits;
    if (exponent == 0x1F)
        bits = sign | 0x7F800000 | (mantissa << 13);
    else if (exponent != 0)
        bits = sign | ((exponent + 112) << 23) | (mantissa << 13);
    else if (mantissa == 0)
        bits = sign;
    else
    {
        exponent = 113;
        while (!(mantissa & 0x400))
        {
            mantissa <<= 1;
            exponent--;
        }
        bits = sign | (exponent << 23) | ((mantissa & 0x3FF) << 13);
    }
    float f;
    memcpy(&f, &bits, sizeof(f));
    return f;
}'''

# recompiler_config.cpp: XenonRecomp prefixes the config's folder to every path in it, so an
# absolute path (the launcher's build recipe gives them, its game and work folders sharing no
# root) fails. Each path is resolved once, right after it is read, and the folder is cleared:
# a relative config gives the same files as before.
CONFIG_ANCHOR = '''        switchTableFilePath = main["switch_table_file_path"].value_or<std::string>("");
'''
CONFIG_ADDITION = CONFIG_ANCHOR + '''
        // (XDroid360) A config path is relative to the config's folder unless it is absolute.
        // Resolved once here, so every later use (recompiler.cpp's loads, the patched-file
        // write, the output folder, the switch table below) takes the path as is.
        auto resolve = [&](std::string& path)
        {
            const bool absolute = !path.empty() &&
                (path[0] == '/' || path[0] == '\\\\' || (path.size() > 1 && path[1] == ':'));
            if (!path.empty() && !absolute)
                path = directoryPath + path;
        };
        resolve(filePath);
        resolve(patchFilePath);
        resolve(patchedFilePath);
        resolve(outDirectoryPath);
        resolve(switchTableFilePath);
        directoryPath.clear();
'''


def write_if_changed(path, text):
    """Writes text unless the file already has it (keeps the timestamp, so builds stay incremental)."""
    if os.path.exists(path) and open(path, encoding='utf-8', newline='').read() == text:
        return False
    open(path, 'w', encoding='utf-8', newline='').write(text)
    return True


def read(path):
    return open(path, encoding='utf-8').read()


def patch_file(path, transform, marker):
    """Writes transform(original) to path. The original is kept next to it as .orig. A file
    without marker (text only our patch adds) is an original: a checkout of another version
    replaces the file, and that version becomes the original. A file with it is patched, by
    this script or an older version of it, and is redone from .orig."""
    orig = path + '.orig'
    current = read(path)
    if marker not in current:
        if not os.path.exists(orig) or read(orig) != current:
            shutil.copyfile(path, orig)
    elif not os.path.exists(orig):
        sys.exit(f'{path} is already patched and its .orig is missing: restore the file from '
                 'XenonRecomp\'s git (git checkout -- <file>) and run again.')
    if write_if_changed(path, transform(read(orig))):
        print('patched', path)


def patch_context_text(s):
    assert s.count(CONTEXT_ANCHOR) == 1, 'ppc_context anchor'
    return s.replace(CONTEXT_ANCHOR, CONTEXT_ADDITION)


def patch_recompiler_text(s):
    for needle in (ANCHOR, OLD_VCMPBFP, OLD_BDNZF, OLD_MFTB, OLD_FCTID, OLD_FCTIDZ, OLD_FCTIWZ, OLD_SWITCH,
                   RLWIMI_OLD, RLDICL_OLD, UPK_OLD, PK_OLD, BLRL_OLD):
        assert s.count(needle) == 1, needle[:60]
    s = s.replace(OLD_VCMPBFP, '').replace(OLD_BDNZF, NEW_BDNZF).replace(OLD_MFTB, NEW_MFTB)
    s = s.replace(OLD_FCTID, NEW_FCTID).replace(OLD_FCTIDZ, NEW_FCTIDZ).replace(OLD_FCTIWZ, NEW_FCTIWZ)
    s = s.replace(OLD_SWITCH, NEW_SWITCH)
    s = s.replace(RLWIMI_OLD, RLWIMI_NEW).replace(RLDICL_OLD, RLDICL_NEW).replace(BLRL_OLD, BLRL_NEW)
    s = s.replace(UPK_OLD, UPK_NEW).replace(PK_OLD, PK_NEW)
    return s.replace(ANCHOR, NEW_CASES + ANCHOR)


def patch_disasm_text(s):
    assert s.count(DIALECT_OLD) == 1, 'disasm dialect'
    return s.replace(DIALECT_OLD, DIALECT_NEW)


def patch_config_text(s):
    assert s.count(CONFIG_ANCHOR) == 1, 'recompiler_config anchor'
    return s.replace(CONFIG_ANCHOR, CONFIG_ADDITION)


def patch(path):
    """Patches recompiler.cpp at path (and recompiler_config.cpp, XenonUtils/ppc_context.h,
    thirdparty/disasm/ppc-dis.c)."""
    patch_file(path, patch_recompiler_text, '// ---- DAO additions')
    patch_file(os.path.join(os.path.dirname(path), 'recompiler_config.cpp'), patch_config_text, '(XDroid360)')
    patch_file(os.path.join(os.path.dirname(path), '..', 'XenonUtils', 'ppc_context.h'), patch_context_text,
               'PPCQueryTimebase')
    patch_file(os.path.join(os.path.dirname(path), '..', 'thirdparty', 'disasm', 'ppc-dis.c'), patch_disasm_text,
               'never 403/405')


def main():
    patch(sys.argv[1])


if __name__ == '__main__':
    main()

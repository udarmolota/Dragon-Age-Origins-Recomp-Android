// The native renderer's hooks in the game's Direct3D (XDroid360, only in a build with the renderer:
// XDROID360_NATIVE_RENDERER). The renderer draws from the GPU ring, and two things it can't read
// there come from the game thread (native-renderer/src/nfsmw_nativo_ganchos.h):
//   - which shader container each D3D shader object was made from (the microcode in the ring is
//     already patched by D3D, so it can't be looked up by content);
//   - which shaders each Draw* had bound, with its primitive type and count, so the ring can pair
//     the draw with its shaders.
// Disc build addresses (the XDK's D3D, statically linked); Title Update 6 has the same library at
// other addresses, not hooked yet.
//   CreateVertexShader sub_82CCC3B8, CreatePixelShader sub_82CCC1D0: r3 the container on entry,
//     the new object in r3 on return (0 on failure).
//   DrawVertices sub_82CD3850 (dev, prim, start, count), DrawIndexedVertices sub_82CD3C40 (dev, prim,
//     base, start, count), DrawVerticesUP sub_82CD3250 (dev, prim, count, data, stride),
//     DrawIndexedVerticesUP sub_82CD37B0 (dev, prim, min index, vertices, count, ...).
//   The device keeps the bound vertex shader at +0x31A0 and the pixel shader at +0x319C
//     (SetVertexShader sub_82CCA8B8, SetPixelShader sub_82CCA6B0).
#include "stdafx.h"

#ifdef XDROID360_NATIVE_RENDERER

#include "kernel/function.h"
#include "kernel/game_build.h"

#include "nfsmw_nativo_ganchos.h"

namespace
{
    namespace nativo = nfsmw::nativo;

    constexpr uint32_t kBoundVertexShader = 0x31A0;
    constexpr uint32_t kBoundPixelShader = 0x319C;

    // The device offsets, set once when the library loads (before the game makes a device).
    struct ConfigureDevice
    {
        ConfigureDevice() { nativo::ConfigurarDispositivoD3D(kBoundVertexShader, kBoundPixelShader); }
    } s_configureDevice;

    template <bool kVertex>
    void CreateShaderHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        const auto* entry = nativo::ganchos_detalle::IdentificarCreacion(base, ctx.r3.u32, kVertex);
        original(ctx, base);
        if (ctx.r3.u32 != 0)
            nativo::ganchos_detalle::RecordarCreacion(ctx.r3.u32, entry, kVertex);
    }

    // r3 the device; r4..r7 as the call has them (the renderer reads type and count from them).
    template <nativo::FuncionDibujo kFunction>
    void DrawHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        nativo::AnotarDibujo(kFunction, base, ctx.r3.u32, ctx.r4.u32, ctx.r5.u32, ctx.r6.u32, ctx.r7.u32);
        original(ctx, base);
        // A record its FlushState didn't take goes to the queue.
        nativo::TerminarDibujo();
    }

    void CreateVertexShaderHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        CreateShaderHook<true>(ctx, base, original);
    }
    void CreatePixelShaderHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        CreateShaderHook<false>(ctx, base, original);
    }
    void DrawVerticesHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        DrawHook<nativo::FuncionDibujo::kVertices>(ctx, base, original);
    }
    void DrawIndexedVerticesHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        DrawHook<nativo::FuncionDibujo::kIndexados>(ctx, base, original);
    }
    void DrawVerticesUPHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        DrawHook<nativo::FuncionDibujo::kVerticesUP>(ctx, base, original);
    }
    void DrawIndexedVerticesUPHook(PPCContext& ctx, uint8_t* base, PPCFunc* original)
    {
        DrawHook<nativo::FuncionDibujo::kIndexadosUP>(ctx, base, original);
    }
}

GAME_HOOK_ONE(sub_82CCC3B8, CreateVertexShaderHook)
GAME_HOOK_ONE(sub_82CCC1D0, CreatePixelShaderHook)
GAME_HOOK_ONE(sub_82CD3850, DrawVerticesHook)
GAME_HOOK_ONE(sub_82CD3C40, DrawIndexedVerticesHook)
GAME_HOOK_ONE(sub_82CD3250, DrawVerticesUPHook)
GAME_HOOK_ONE(sub_82CD37B0, DrawIndexedVerticesUPHook)

#endif // XDROID360_NATIVE_RENDERER

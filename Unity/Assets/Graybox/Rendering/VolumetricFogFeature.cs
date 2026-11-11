using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

namespace Storypinner.Rendering
{
    // Renderer feature URP care deseneaza ceata volumetrica (VolumetricFog.shader) peste imagine,
    // inainte de post-processing (ca bloom-ul sa prinda si razele lunii).
    // Pasul declara toate texturile globale (shadow map-ul lunii) si depth-ul camerei,
    // ca Render Graph sa le tina valide pana aici.
    public class VolumetricFogFeature : ScriptableRendererFeature
    {
        public Material material;
        public RenderPassEvent passEvent = RenderPassEvent.BeforeRenderingPostProcessing;

        FogPass pass;

        public override void Create()
        {
            pass = new FogPass { renderPassEvent = passEvent };
        }

        public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
        {
            if (material == null)
                return;
            var type = renderingData.cameraData.cameraType;
            if (type == CameraType.Preview || type == CameraType.Reflection)
                return;
            pass.material = material;
            pass.ConfigureInput(ScriptableRenderPassInput.Depth);
            renderer.EnqueuePass(pass);
        }

        class FogPass : ScriptableRenderPass
        {
            public Material material;

            class PassData
            {
                public Material material;
            }

            public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
            {
                var resources = frameData.Get<UniversalResourceData>();
                using var builder = renderGraph.AddRasterRenderPass<PassData>("Storypinner Volumetric Fog", out var data);
                data.material = material;
                builder.UseAllGlobalTextures(true);
                if (resources.cameraDepthTexture.IsValid())
                    builder.UseTexture(resources.cameraDepthTexture);
                builder.SetRenderAttachment(resources.activeColorTexture, 0, AccessFlags.ReadWrite);
                builder.SetRenderFunc(static (PassData d, RasterGraphContext ctx) =>
                    Blitter.BlitTexture(ctx.cmd, new Vector4(1f, 1f, 0f, 0f), d.material, 0));
            }
        }
    }
}

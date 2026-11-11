// Ceata volumetrica pentru camera Storypinner (night mode).
// Pentru fiecare pixel merge pe raza de la camera pana la suprafata (raymarching) si aduna lumina:
//  - densitatea e 3D: mai deasa in colturile camerei si langa podea, cu zgomot care se misca incet
//  - lumina lunii vine din shadow map-ul luminii directionale, deci razele de la fereastra sunt reale
//    (taiate de rama, perdele, birou) si se vad din orice unghi, in ambii ochi in VR
//  - benzile LED de sub tavan si cateva lampi (fara umbre) coloreaza si ele ceata
// Rezultatul se compune peste imagine cu Blend One SrcAlpha: rgb = lumina din ceata, a = cat trece prin ea.
Shader "Hidden/Storypinner/VolumetricFog"
{
    Properties
    {
        _RoomMin ("Room Min", Vector) = (0, 0, 0, 0)
        _RoomMax ("Room Max", Vector) = (1, 1, 1, 0)
        _FogColor ("Ambient fog color (rgb), base density (a)", Vector) = (0.01, 0.016, 0.045, 0.06)
        _CornerParams ("Corner density, corner radius, floor density, floor height", Vector) = (0.55, 1.2, 0.25, 0.6)
        _MoonParams ("Moon strength, anisotropy, extinction, max distance", Vector) = (6, 0.55, 1, 20)
        _NeonColor ("Neon color (rgb), band height (a)", Vector) = (0.02, 0.05, 0.18, 0.5)
        _NoiseParams ("Noise scale, strength, speed", Vector) = (0.6, 0.6, 0.08, 0)
        _P0 ("Point light 0 pos (xyz), range (w)", Vector) = (0, 0, 0, 0)
        _P1 ("Point light 1", Vector) = (0, 0, 0, 0)
        _P2 ("Point light 2", Vector) = (0, 0, 0, 0)
        _P3 ("Point light 3", Vector) = (0, 0, 0, 0)
        _C0 ("Point light 0 color", Vector) = (0, 0, 0, 0)
        _C1 ("Point light 1 color", Vector) = (0, 0, 0, 0)
        _C2 ("Point light 2 color", Vector) = (0, 0, 0, 0)
        _C3 ("Point light 3 color", Vector) = (0, 0, 0, 0)
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" }
        ZWrite Off ZTest Always Cull Off
        Blend One SrcAlpha

        Pass
        {
            Name "VolumetricFog"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma target 3.5
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Random.hlsl"
            #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"

            #define STEPS 48

            float4 _RoomMin, _RoomMax, _FogColor, _CornerParams, _MoonParams, _NeonColor, _NoiseParams;
            float4 _P0, _P1, _P2, _P3, _C0, _C1, _C2, _C3;

            float Hash(float3 p)
            {
                p = frac(p * 0.3183099 + 0.1);
                p *= 17.0;
                return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
            }

            float ValueNoise(float3 x)
            {
                float3 i = floor(x);
                float3 f = frac(x);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(
                    lerp(lerp(Hash(i), Hash(i + float3(1, 0, 0)), f.x),
                         lerp(Hash(i + float3(0, 1, 0)), Hash(i + float3(1, 1, 0)), f.x), f.y),
                    lerp(lerp(Hash(i + float3(0, 0, 1)), Hash(i + float3(1, 0, 1)), f.x),
                         lerp(Hash(i + float3(0, 1, 1)), Hash(i + float3(1, 1, 1)), f.x), f.y), f.z);
            }

            // cata ceata e intr-un punct din camera
            float Density(float3 p)
            {
                if (any(p < _RoomMin.xyz) || any(p > _RoomMax.xyz))
                    return 0.0; // afara (dincolo de fereastra) nu e ceata
                float dx = min(p.x - _RoomMin.x, _RoomMax.x - p.x);
                float dz = min(p.z - _RoomMin.z, _RoomMax.z - p.z);
                float corner = exp(-length(float2(dx, dz)) / _CornerParams.y);
                float wall = exp(-min(dx, dz) / (_CornerParams.y * 0.5));
                float floorFog = exp(-(p.y - _RoomMin.y) / _CornerParams.w);
                float t = _Time.y * _NoiseParams.z;
                float n = ValueNoise(p * _NoiseParams.x + float3(t, t * 0.3, -t * 0.6)) * 0.65
                        + ValueNoise(p * _NoiseParams.x * 2.3 - float3(t * 0.5, 0, t)) * 0.35;
                float d = _FogColor.a + _CornerParams.x * (corner + 0.3 * wall) + _CornerParams.z * floorFog;
                return d * lerp(1.0 - _NoiseParams.y, 1.0 + _NoiseParams.y, n);
            }

            float HenyeyGreenstein(float cosTheta, float g)
            {
                float g2 = g * g;
                return (1.0 - g2) / (4.0 * PI * pow(max(1.0 + g2 - 2.0 * g * cosTheta, 1e-3), 1.5));
            }

            float3 PointGlow(float3 p, float4 pos, float4 col)
            {
                float3 v = pos.xyz - p;
                float r2 = dot(v, v);
                float a = saturate(1.0 - r2 / max(pos.w * pos.w, 1e-4));
                return col.rgb * a * a / (1.0 + r2 * 4.0);
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                float2 uv = input.positionCS.xy / _ScaledScreenParams.xy;
            #if UNITY_REVERSED_Z
                float depth = SampleSceneDepth(uv);
            #else
                float depth = lerp(UNITY_NEAR_CLIP_VALUE, 1, SampleSceneDepth(uv));
            #endif
                float3 posWS = ComputeWorldSpacePosition(uv, depth, UNITY_MATRIX_I_VP);
                float3 cam = GetCameraPositionWS();
                float3 ray = posWS - cam;
                float dist = length(ray);
                float3 dir = ray / max(dist, 1e-4);
                dist = min(dist, _MoonParams.w);

                float stepLen = dist / STEPS;
                float jitter = InterleavedGradientNoise(input.positionCS.xy, 0);
                float3 p = cam + dir * stepLen * jitter;

                Light moonLight = GetMainLight();
                float cosTheta = dot(dir, moonLight.direction);
                float phase = lerp(1.0 / (4.0 * PI), HenyeyGreenstein(cosTheta, _MoonParams.y), 0.6);
                float3 moon = moonLight.color * _MoonParams.x * phase;
                float extinction = max(_MoonParams.z, 1e-3);

                float transmittance = 1.0;
                float3 scattered = 0.0;
                [loop]
                for (int i = 0; i < STEPS; i++)
                {
                    float d = Density(p);
                    if (d > 1e-4)
                    {
                        float shadow = MainLightRealtimeShadow(TransformWorldToShadowCoord(p));
                        float3 light = _FogColor.rgb + moon * shadow;
                        light += _NeonColor.rgb * exp(-(_RoomMax.y - p.y) / _NeonColor.a);
                        light += PointGlow(p, _P0, _C0) + PointGlow(p, _P1, _C1) + PointGlow(p, _P2, _C2) + PointGlow(p, _P3, _C3);
                        float stepT = exp(-d * extinction * stepLen);
                        scattered += transmittance * light * (1.0 - stepT) / extinction;
                        transmittance *= stepT;
                    }
                    p += dir * stepLen;
                }
                return half4(scattered, transmittance);
            }
            ENDHLSL
        }
    }
}

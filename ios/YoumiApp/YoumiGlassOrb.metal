#include <metal_stdlib>
using namespace metal;

[[ stitchable ]] half4 youmiGlassOrb(float2 position, half4 source, float2 size,
                                  float time, float energy, float warmth, float speed) {
    float diameter = max(min(size.x, size.y), 1.0);
    float2 p = (position - size * 0.5) / (diameter * 0.43);
    float radius = length(p);
    float antialias = 2.0 / diameter;
    float alpha = 1.0 - smoothstep(1.0 - antialias, 1.0, radius);
    if (alpha <= 0.0) return half4(0.0);

    float depth = sqrt(max(1.0 - dot(p, p), 0.0));
    float3 normal = float3(p, depth);
    float t = time * 0.34;
    float2 q = p * (0.80 + 0.24 * depth);
    q += (0.13 + (speed - 1.0) * 0.08)
        * float2(sin(q.y * 3.2 + t), cos(q.x * 2.7 - t * 0.7));
    float flow = q.y + 0.46 * sin(q.x * 2.9 + t * 0.65)
        + 0.17 * sin(q.x * 5.7 - t * 0.45);
    float fold = sin(q.x * 2.0 - q.y * 2.3 + t * 0.5);

    float3 indigo = float3(0.022, 0.025, 0.105);
    float3 violet = float3(0.24, 0.045, 0.47);
    float3 blue = float3(0.025, 0.25, 0.82);
    float3 coral = mix(float3(0.74, 0.075, 0.37), float3(1.0, 0.30, 0.14), warmth);
    float3 color = mix(indigo, violet, 0.28 + 0.33 * depth);
    color = mix(color, blue, (1.0 - smoothstep(-0.75, 0.05, flow)) * (0.52 + 0.27 * depth));

    float warmSheet = smoothstep(-0.08, 0.16, flow) * (1.0 - smoothstep(0.34, 0.70, flow));
    color = mix(color, coral, warmSheet * (0.45 + 0.45 * depth));
    float foldLight = exp(-pow((flow - 0.25) * 9.0, 2.0));
    color += foldLight * float3(1.0, 0.48 + warmth * 0.18, 0.28) * (0.4 + 0.6 * depth);
    color += exp(-pow((flow + 0.35) * 7.0, 2.0)) * float3(0.10, 0.20, 0.58) * 0.6;
    color *= 0.85 + 0.15 * fold;

    float fresnel = pow(1.0 - depth, 2.8);
    float rim = exp(-pow((radius - 0.973) * 90.0, 2.0));
    float lowerReflection = pow(max(dot(normal, normalize(float3(-0.45, 0.68, 0.32))), 0.0), 9.0);
    float upperReflection = pow(max(dot(normal, normalize(float3(-0.30, -0.73, 0.58))), 0.0), 65.0);
    float softReflection = pow(max(dot(normal, normalize(float3(0.62, -0.45, 0.42))), 0.0), 15.0);
    color += fresnel * float3(0.10, 0.25, 0.62);
    color += rim * float3(0.45, 0.68, 1.0) * (0.45 + 0.25 * sin(p.y * 5.0));
    color += lowerReflection * float3(0.30, 0.62, 0.90);
    color += upperReflection * float3(0.90, 0.91, 1.0) * 0.95;
    color += softReflection * float3(0.31, 0.35, 0.68) * 0.6;
    color *= 1.0 + min(energy, 1.0) * 0.09;
    return half4(half3(clamp(color, 0.0, 1.0) * alpha), half(alpha));
}

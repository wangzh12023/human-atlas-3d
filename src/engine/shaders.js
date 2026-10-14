// GLSL for the atlas meshes. Written for WebGL2 / GLSL ES 3.00 (material.glslVersion = GLSL3).
//
// Per-vertex data (interleaved Uint16, see pipeline/export.py):
//   aPM  : quantised male position        aPF : quantised female position
//   aPid : piece index                    aAO : aoM + aoF * 256
//   aNrm : (packed i8x2 male normal, packed i8x2 female normal)
//
// Per-piece data lives in two float textures (see atlas.js):
//   uState (256 wide, 1 texel / piece)  : visibility, hover, selected, ghost
//   uData  (2048 wide, 8 texels / piece): 0 colour+material, 1 centre M (+stagger), 2 centre F,
//                                         3 grid M (+scale), 4 grid F (+scale), 5 separation offset,
//                                         6/7 optional breast footprint for root color blending

export const common = /* glsl */ `
precision highp float;
precision highp int;
precision highp sampler2D;

uniform sampler2D uState;
uniform sampler2D uData;
uniform vec3 uQMin;
uniform vec3 uQScale;
uniform float uMorph;
uniform float uExplodeA;
uniform float uExplodeB;
uniform float uArc;
uniform float uTime;

vec4 stateFetch(int pid) {
  return texelFetch(uState, ivec2((pid & 255) << 1, pid >> 8), 0);
}
vec4 state2Fetch(int pid) {
  return texelFetch(uState, ivec2(((pid & 255) << 1) + 1, pid >> 8), 0);
}
vec4 dataFetch(int pid, int k) {
  return texelFetch(uData, ivec2(((pid & 255) << 3) + k, pid >> 8), 0);
}
vec2 unpackI8x2(float v) {
  float hi = floor(v / 256.0);
  float lo = v - hi * 256.0;
  lo = lo > 127.5 ? lo - 256.0 : lo;
  hi = hi > 127.5 ? hi - 256.0 : hi;
  return vec2(lo, hi) / 127.0;
}
vec3 octDecode(vec2 e) {
  vec3 v = vec3(e.xy, 1.0 - abs(e.x) - abs(e.y));
  if (v.z < 0.0) {
    vec2 s = vec2(v.x >= 0.0 ? 1.0 : -1.0, v.y >= 0.0 ? 1.0 : -1.0);
    v.xy = (1.0 - abs(v.yx)) * s;
  }
  return normalize(v);
}

// Position of a vertex after morph + explode. Returns world-space position.
vec3 atlasPosition(int pid, vec3 posM, vec3 posF, out float flight) {
  vec3 p = mix(posM, posF, uMorph);
  vec4 cM = dataFetch(pid, 1);
  vec4 cF = dataFetch(pid, 2);
  vec3 c = mix(cM.xyz, cF.xyz, uMorph);
  vec3 local = p - c;
  vec4 sep = dataFetch(pid, 5);
  vec3 sepC = c + sep.xyz * uExplodeA;
  float stagger = cM.w;
  float t = clamp(uExplodeB * 1.5 - stagger * 0.5, 0.0, 1.0);
  t = t * t * (3.0 - 2.0 * t);
  flight = t;
  if (t <= 0.0) return sepC + local;
  vec4 gM = dataFetch(pid, 3);
  vec4 gF = dataFetch(pid, 4);
  vec3 gc = mix(gM.xyz, gF.xyz, uMorph);
  float gs = mix(gM.w, gF.w, uMorph);
  vec3 center = mix(sepC, gc, t);
  center.z += sin(t * 3.14159265) * uArc * (0.35 + stagger);
  return center + local * mix(1.0, gs, t);
}
`;

export const atlasVertex = /* glsl */ `
${common}
in vec3 aPM;
in float aPid;
in vec3 aPF;
in float aAO;
in vec2 aNrm;

out vec3 vNormal;
out vec3 vViewPos;
out vec3 vWorldPos;
out float vAO;
out float vBreastBlend;
flat out int vPid;
flat out vec4 vSt;
flat out vec4 vSt2;
flat out vec4 vCol;

void main() {
  int pid = int(aPid + 0.5);
  vec4 st = stateFetch(pid);
  vPid = pid;
  vSt = st;
  vSt2 = state2Fetch(pid);
#ifdef GHOST
  if (st.x < 0.002 || st.w < 0.002) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
#else
  if (st.x < 0.002 || st.w > 0.998) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
#endif
  vec3 posM = uQMin + aPM * uQScale;
  vec3 posF = uQMin + aPF * uQScale;
  float flight;
  vec3 wp = atlasPosition(pid, posM, posF, flight);
  vec3 nM = octDecode(unpackI8x2(aNrm.x));
  vec3 nF = octDecode(unpackI8x2(aNrm.y));
  vec3 n = normalize(mix(nM, nF, uMorph));
  float aoF = floor(aAO / 256.0);
  float aoM = aAO - aoF * 256.0;
  vAO = mix(aoM, aoF, uMorph) / 255.0;
  vCol = dataFetch(pid, 0);
  // Evaluate before explode/grid transforms so the tissue's root color stays
  // attached to its own geometry at every layout and morph state.
  vec4 breast = dataFetch(pid, 6);
  vec4 breastExtra = dataFetch(pid, 7);
  vBreastBlend = 1.0;
  if (breastExtra.y > 0.5) {
    float dy = posF.y - breast.y;
    float upper = smoothstep(0.0, breast.w, dy);
    float cx = breast.x + 8.0 * upper;
    float rx = breast.z * (1.0 - 0.22 * upper);
    float t = 1.0 / (1.0 + exp(-2.0 * dy / 28.0));
    float ry = mix(breastExtra.x, breast.w, t);
    vec2 q = vec2((abs(posF.x) - cx) / rx, dy / ry);
    vBreastBlend = smoothstep(0.0, 0.55, 1.0 - dot(q, q));
  }
  vec4 mv = viewMatrix * vec4(wp, 1.0);
  vViewPos = mv.xyz;
  vWorldPos = wp;
  vNormal = normalize(mat3(viewMatrix) * n);
  gl_Position = projectionMatrix * mv;
}
`;

export const atlasFragment = /* glsl */ `
precision highp float;
precision highp int;
uniform float uTime;
uniform vec3 uSelColor;
uniform vec3 uMuscleColor;
uniform float uGhostOpacity;
in vec3 vNormal;
in vec3 vViewPos;
in vec3 vWorldPos;
in float vAO;
in float vBreastBlend;
flat in int vPid;
flat in vec4 vSt;
flat in vec4 vSt2;
flat in vec4 vCol;
out vec4 fragColor;

float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
vec3 toSRGB(vec3 c) {
  return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}

void main() {
  float vis = vSt.x;
#ifndef GHOST
  float keep = vis * (1.0 - vSt.w);
  if (keep < 0.999) {
    // interleaved gradient noise: an even, film-grain-like dissolve (per-piece offset avoids pattern locking)
    vec2 fc = gl_FragCoord.xy + vec2(float(vPid % 61) * 5.588, float(vPid % 37) * 3.17);
    float n = fract(52.9829189 * fract(dot(fc, vec2(0.06711056, 0.00583715))));
    if (n > keep) discard;
  }
#endif
  vec3 N = normalize(vNormal);
  if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(-vViewPos);
  float NdV = clamp(dot(N, V), 0.0, 1.0);
#ifdef GHOST
  float fres = pow(1.0 - NdV, 2.2);
  float a = (0.035 + 0.30 * fres) * vSt.w * vis * uGhostOpacity;
  vec3 gcol = mix(vec3(0.74, 0.77, 0.79), vCol.rgb, 0.25);
  fragColor = vec4(toSRGB(gcol), a);
  return;
#else
  vec3 albedo = mix(uMuscleColor, vCol.rgb, vBreastBlend);
  float mat = vCol.a;           // 0 = soft tissue (wet), 1 = bone / matte
  float hover = vSt.y;
  float sel = vSt.z;
  albedo = mix(albedo, uSelColor, sel * 0.78);
  albedo = mix(albedo, albedo * 1.18 + 0.05, hover * 0.9);

  float ao = mix(1.0, vAO, 0.72);
  // soft studio rig in view space (key from upper-left-front, fill from right, back rim)
  vec3 L1 = normalize(vec3(-0.38, 0.55, 0.74));
  vec3 L2 = normalize(vec3(0.80, 0.05, 0.50));
  vec3 L3 = normalize(vec3(0.10, 0.60, -0.80));
  float wrap = mix(0.55, 0.25, mat);
  float d1 = max((dot(N, L1) + wrap) / (1.0 + wrap), 0.0);
  float d2 = max((dot(N, L2) + wrap) / (1.0 + wrap), 0.0);
  float d3 = max(dot(N, L3), 0.0);
  float hemi = 0.5 + 0.5 * N.y;
  vec3 amb = mix(vec3(0.50, 0.48, 0.48), vec3(0.70, 0.70, 0.72), hemi);
  vec3 col = albedo * (amb * ao * 0.85 + vec3(1.0, 0.985, 0.96) * d1 * (0.45 + 0.55 * ao) * 0.72 + vec3(0.85, 0.90, 0.98) * d2 * ao * 0.26);
  // subsurface-ish warm bleed for soft tissue
  col += albedo * (1.0 - mat) * 0.10 * pow(1.0 - NdV, 1.5) * ao;
  // specular (wet tissue = sharper)
  vec3 H = normalize(L1 + V);
  float shin = mix(38.0, 14.0, mat);
  float spec = pow(max(dot(N, H), 0.0), shin) * mix(0.16, 0.05, mat);
  col += vec3(spec) * ao;
  // rim
  col += vec3(0.96, 0.97, 1.0) * pow(1.0 - NdV, 3.0) * (0.08 + 0.22 * d3) * ao;
  // selection glow pulse
  col += uSelColor * sel * (0.06 + 0.05 * sin(uTime * 3.2)) ;
  float dim = vSt2.x;
  vec3 grey = vec3(dot(col, vec3(0.299, 0.587, 0.114)));
  col = mix(col, grey * 0.92 + 0.07, dim * 0.72);
  // gentle filmic shoulder
  col = col / (1.0 + col * 0.08);
  fragColor = vec4(toSRGB(clamp(col, 0.0, 1.0)), 1.0);
#endif
}
`;

export const pickVertex = /* glsl */ `
${common}
in vec3 aPM;
in float aPid;
in vec3 aPF;
flat out int vPid;
void main() {
  int pid = int(aPid + 0.5);
  vec4 st = stateFetch(pid);
  vPid = pid;
  if (st.x < 0.5 || st.w > 0.5) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  vec3 posM = uQMin + aPM * uQScale;
  vec3 posF = uQMin + aPF * uQScale;
  float flight;
  vec3 wp = atlasPosition(pid, posM, posF, flight);
  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
}
`;

export const pickFragment = /* glsl */ `
precision highp float;
precision highp int;
flat in int vPid;
out vec4 fragColor;
void main() {
  int id = vPid + 1;
  fragColor = vec4(float(id & 255) / 255.0, float((id >> 8) & 255) / 255.0, float((id >> 16) & 255) / 255.0, 1.0);
}
`;

export const shadowVertex = /* glsl */ `
out vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const shadowFragment = /* glsl */ `
precision highp float;
uniform float uOpacity;
in vec2 vUv;
out vec4 fragColor;
void main() {
  vec2 p = (vUv - 0.5) * 2.0;
  float d = length(p * vec2(1.0, 1.9));
  float a = exp(-d * d * 3.2) * 0.22 + exp(-d * d * 18.0) * 0.12;
  fragColor = vec4(0.28, 0.27, 0.26, a * uOpacity);
}
`;

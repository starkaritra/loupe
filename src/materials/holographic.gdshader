shader_type spatial;
// Med-high HOLOGRAPHIC look (LP-006): translucent shells with bright fresnel RIMS and a dim interior —
// a real hologram, not an additive blob. Alpha-blended (not blend_add) so dense/overlapping geometry
// reads with form and depth instead of saturating to white. Restrained Tron/JARVIS palette. Per-entity
// tint/glow/selected are uniforms so a lens can theme coherently.
render_mode blend_mix, cull_disabled, depth_draw_opaque, shadows_disabled, specular_disabled, diffuse_lambert;

uniform vec3 tint : source_color = vec3(0.30, 0.75, 1.0);
uniform float glow : hint_range(0.0, 4.0) = 1.4;
uniform float base_alpha : hint_range(0.0, 1.0) = 0.10;
uniform float fresnel_power : hint_range(0.5, 8.0) = 3.0;
uniform float rim_boost : hint_range(0.0, 4.0) = 1.6;
uniform float selected : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	// NORMAL and VIEW are in view space; fresnel peaks at grazing angles (the rim).
	float ndv = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float fres = pow(1.0 - ndv, fresnel_power);

	// Dim translucent interior, bright emissive rim.
	ALBEDO = tint * 0.08;
	EMISSION = tint * (glow * (0.12 + fres * rim_boost)) + tint * selected * 0.5;
	ALPHA = clamp(base_alpha + fres * 0.7 + selected * 0.2, 0.0, 0.92);
	RIM = 0.2;
	ROUGHNESS = 1.0;
}

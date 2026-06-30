class_name Lens
extends RefCounted

## A Lens turns ONE entity's typed payload into scene visuals (the specialized half of the
## shell/lens split, LP-002). It renders only this entity's own payload — the Stage handles hierarchy,
## explode, and LOD. Subclasses override `payload_type()` and `render()`.

func payload_type() -> String:
	return "none"

## Build the Node3D visual for `entity`. `ctx` provides shared, theme-coherent helpers.
func render(_entity: LoupeIR.Entity, _ctx: Context) -> Node3D:
	return Node3D.new()


## Shared services handed to every lens so visuals stay holographically coherent (LP-006).
class Context:
	extends RefCounted

	const _SHADER_PATH := "res://src/materials/holographic.gdshader"
	var _shader: Shader = null

	func _init() -> void:
		_shader = load(_SHADER_PATH) as Shader

	## A holographic ShaderMaterial themed per call. tint is linear RGB; glow scales emission.
	func holo_material(tint: Color, glow: float = 1.4) -> ShaderMaterial:
		var m := ShaderMaterial.new()
		m.shader = _shader
		m.set_shader_parameter("tint", Vector3(tint.r, tint.g, tint.b))
		m.set_shader_parameter("glow", glow)
		return m

	## Crisp in-scene typography (LP-006). Billboarded so labels stay readable from any angle.
	func make_label(text: String, size: float = 0.12, color: Color = Color(0.8, 0.92, 1.0)) -> Label3D:
		var l := Label3D.new()
		l.text = text
		l.font_size = 64
		l.pixel_size = size / 64.0
		l.modulate = color
		l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		l.no_depth_test = false
		l.shaded = false
		l.outline_size = 0
		return l

	## Unlit, additive, transparent line material for edges/wireframe (graph/connectome lenses).
	func line_material(color: Color) -> StandardMaterial3D:
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.vertex_color_use_as_albedo = true
		m.albedo_color = color
		m.disable_receive_shadows = true
		return m

	const _EQN_DIR := "res://assets/eqn/"
	var _eqn_index: Dictionary = {}

	## A persistent LaTeX label below a component (payload.data.eqn id) — pre-rendered PNG, billboarded.
	func eqn_sprite(eqn_id: String) -> Sprite3D:
		if eqn_id == "":
			return null
		if _eqn_index.is_empty():
			var f := FileAccess.open(_EQN_DIR + "index.json", FileAccess.READ)
			if f != null:
				var d: Variant = JSON.parse_string(f.get_as_text())
				if d is Dictionary: _eqn_index = d
		var file := String(_eqn_index.get(eqn_id, ""))
		if file == "": return null
		var s := Sprite3D.new()
		s.texture = load(_EQN_DIR + file) as Texture2D
		s.billboard = BaseMaterial3D.BILLBOARD_ENABLED; s.shaded = false; s.pixel_size = 0.0013
		return s

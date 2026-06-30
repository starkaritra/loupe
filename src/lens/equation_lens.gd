class_name EquationLens
extends Lens

## Lens for `equation` payloads — shows a real LaTeX formula as a crisp billboarded image (pre-rendered
## offline by tools/render_equations.py → assets/eqn/<hash>.png, mapped by index.json). $0, no services.
##   payload.data = { id: "attention", scale?: float, glow?: float }

const _DIR := "res://assets/eqn/"
var _index: Dictionary = {}


func payload_type() -> String:
	return "equation"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var root := Node3D.new()
	root.name = "equation_visual"
	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var tex := _load(String(spec.get("id", "")))
	if tex == null:
		if entity.label != "":
			root.add_child(ctx.make_label(entity.label, 0.1))
		return root
	var s := Sprite3D.new()
	s.texture = tex
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	s.shaded = false
	s.modulate = Color(1, 1, 1, 0.95)
	var px := float(spec.get("scale", 1.0)) * 0.0016
	s.pixel_size = px
	root.add_child(s)
	return root


func _load(id: String) -> Texture2D:
	if _index.is_empty():
		var f := FileAccess.open(_DIR + "index.json", FileAccess.READ)
		if f != null:
			var d: Variant = JSON.parse_string(f.get_as_text())
			if d is Dictionary:
				_index = d
	var file := String(_index.get(id, ""))
	if file == "":
		return null
	return load(_DIR + file) as Texture2D

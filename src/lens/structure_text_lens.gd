class_name StructureTextLens
extends Lens

## Lens for `text` payloads — the DELIBERATELY OPPOSITE domain to mesh (a paper/book/outline has
## hierarchy but no physical geometry). Proves the shell is universal: same explode/zoom/drill, totally
## different payload. Renders a translucent holographic "card" plus crisp billboarded typography
## (title + the entity's content tier).
##   payload.data = { accent: [r,g,b], width: f, height: f } (all optional)

func payload_type() -> String:
	return "text"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var root := Node3D.new()
	root.name = "text_visual"

	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var accent := _color(spec.get("accent"), Color(0.45, 0.95, 0.8))
	var w := float(spec.get("width", 1.6))
	var h := float(spec.get("height", 1.0))

	var card := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(w, h)
	card.mesh = quad
	card.material_override = ctx.holo_material(accent, 0.9)
	root.add_child(card)

	var title := ctx.make_label(entity.label, 0.16, Color(0.9, 1.0, 0.95))
	title.position = Vector3(0, h * 0.5 + 0.12, 0.02)
	root.add_child(title)

	var body_text := entity.tier("overview")
	if body_text == "":
		body_text = entity.tier("detail")
	if body_text != "":
		var body := ctx.make_label(_wrap(body_text, 28), 0.075, Color(0.75, 0.9, 0.95))
		body.position = Vector3(0, 0, 0.02)
		root.add_child(body)

	var eq := ctx.eqn_sprite(String(spec.get("eqn", "")))
	if eq != null:
		eq.position = Vector3(0, -h * 0.5 - 0.28, 0.02)
		root.add_child(eq)

	return root


## Naive word-wrap so long overview strings stay legible on the card.
func _wrap(text: String, width: int) -> String:
	var out := ""
	var line_len := 0
	for word in text.split(" ", false):
		if line_len + word.length() + 1 > width and line_len > 0:
			out += "\n"
			line_len = 0
		elif line_len > 0:
			out += " "
			line_len += 1
		out += word
		line_len += word.length()
	return out


func _color(v: Variant, fallback: Color) -> Color:
	if v is Array and v.size() >= 3:
		return Color(float(v[0]), float(v[1]), float(v[2]))
	return fallback

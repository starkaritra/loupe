class_name ConvLens
extends Lens

## Lens for `conv` payloads — shows convolution WORKING: a KxK kernel slides over a padded input grid;
## the covered cells light up and the corresponding output feature-map cell fills in. Illustrative dims
## are honest (labelled), values decorative. Serves CNN conv layers (AlexNet/ResNet/VGG).
##   payload.data = { in?: int, k?: int, stride?: int, pad?: int, accent?:[r,g,b], note?: str }

const _CELL := 0.16


func payload_type() -> String:
	return "conv"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var viz := ConvViz.new()
	viz.setup(int(spec.get("in", 9)), int(spec.get("k", 3)), int(spec.get("stride", 1)), int(spec.get("pad", 1)),
		_color(spec.get("accent"), Color(0.55, 0.9, 1.0)), ctx)
	viz.name = "conv_visual"
	return viz


func _color(v: Variant, fb: Color) -> Color:
	return Color(float(v[0]), float(v[1]), float(v[2])) if v is Array and v.size() >= 3 else fb


class ConvViz:
	extends Node3D
	var n := 9
	var k := 3
	var stride := 1
	var pad := 1
	var accent := Color(0.55, 0.9, 1.0)
	var ctx: Lens.Context
	var kernel: MeshInstance3D
	var out_cells: Array = []
	var ow := 0
	var t := 0.0

	func setup(_n, _k, _s, _p, c, _ctx) -> void:
		n = _n; k = _k; stride = _s; pad = _p; accent = c; ctx = _ctx
		var pn := n + 2 * pad
		ow = (pn - k) / stride + 1
		_grid(-1.2, pn, accent.darkened(0.4), pad)   # padded input (pad ring dim)
		_grid(1.4, ow, accent.darkened(0.2), 0, true) # output feature map
		# sliding kernel window over the input
		kernel = MeshInstance3D.new()
		var b := BoxMesh.new(); b.size = Vector3(k * 0.16, k * 0.16, 0.02)
		kernel.mesh = b; kernel.material_override = ctx.holo_material(Color(1, 0.9, 0.5), 2.5)
		add_child(kernel)
		add_child(_label("input + zero-pad", -1.2))
		add_child(_label("feature map", 1.4))

	func _grid(cx: float, side: int, col: Color, ring: int, store := false) -> void:
		var s := 1.4 / float(side)
		for r in side:
			for cc in side:
				var mi := MeshInstance3D.new(); var q := QuadMesh.new(); q.size = Vector2(s * 0.9, s * 0.9)
				mi.mesh = q
				var pad_cell := ring > 0 and (r < ring or cc < ring or r >= side - ring or cc >= side - ring)
				mi.material_override = ctx.holo_material(col.darkened(0.5) if pad_cell else col, 1.0)
				mi.position = Vector3(cx - 0.7 + cc * s, 0.7 - r * s, 0)
				add_child(mi)
				if store: out_cells.append(mi)

	func _process(delta: float) -> void:
		t += delta * 0.5
		var total := ow * ow
		var idx := int(t) % maxi(total, 1)
		var f: float = t - floor(t)
		var oy := idx / ow; var ox := idx % ow
		var pn := n + 2 * pad; var s := 1.4 / float(pn)
		kernel.position = Vector3(-1.2 - 0.7 + (ox + k * 0.5) * s, 0.7 - (oy + k * 0.5) * s, 0.04)
		for i in out_cells.size():
			out_cells[i].material_override.set_shader_parameter("selected", 1.0 if i == idx else 0.0)

	func _label(txt: String, cx: float) -> Label3D:
		var l := ctx.make_label(txt, 0.07, Color(0.8, 0.92, 1.0)); l.position = Vector3(cx, -0.95, 0.02); return l

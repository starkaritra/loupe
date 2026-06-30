class_name MatrixLens
extends Lens

## Lens for `matrix` payloads — a holographic heatmap grid (data-contract.md §5/§7): serves transformer
## weight/embedding matrices, attention patterns, connectivity matrices, any 2D field of scalars.
##   payload.data = {
##     values?:  [[f, ...], ...],   # 2D row-major scalars → rendered faithfully (block-downsampled to fit)
##     rows?: int, cols?: int,      # true dimensions; when `values` is absent the grid is SCHEMATIC —
##                                  #   a dimension-accurate placeholder surface, not fabricated data
##     square?: bool,               # hint for a square matrix of unknown size (e.g. an attention head)
##     accent?: [r,g,b],            # high-value color of the heatmap ramp
##     vmin?: f, vmax?: f,          # explicit color scale (else auto from values, or 0..1 schematic)
##     note?: str,                  # short caption shown under the grid (e.g. "attention pattern")
##     glow?: f
##   }
## A matrix can be enormous (e.g. 50257x768), so the grid is capped to `_MAX_SIDE` cells per axis: real
## values are block-averaged down to fit; schematic grids are sampled at the same cap while preserving the
## true rows:cols aspect ratio. The whole grid is fit to a consistent on-screen size like the graph lens.

const _TARGET_SIZE := 2.4    # longest side of the rendered grid, in scene units
const _MAX_SIDE := 28        # max rendered cells per axis (keeps a giant matrix cheap + legible)
const _MAX_ASPECT := 6.0     # clamp extreme width:height so a tall/wide matrix stays a visible strip


func payload_type() -> String:
	return "matrix"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var root := Node3D.new()
	root.name = "matrix_visual"

	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var accent := _color(spec.get("accent"), Color(0.55, 0.85, 1.0))
	var glow := float(spec.get("glow", 1.2))
	var note := String(spec.get("note", ""))

	# Resolve a capped (rows x cols) grid of normalized [0,1] cell values from whichever inputs exist.
	var grid := _resolve_grid(spec)
	var cells: Array = grid["cells"]            # Array[Array[float]] (rows of normalized values)
	var rows: int = grid["rows"]
	var cols: int = grid["cols"]
	var schematic: bool = grid["schematic"]
	var true_rows: int = grid["true_rows"]
	var true_cols: int = grid["true_cols"]
	if rows <= 0 or cols <= 0:
		return root

	# Fit to a consistent size, preserving the true aspect ratio (longest axis → _TARGET_SIZE). Extreme
	# aspects (e.g. a 50257x512 embedding ≈ 98:1) are clamped to _MAX_ASPECT so the grid stays a visible
	# strip rather than a 1px line — the label always reports the TRUE dimensions.
	var aspect := clampf(float(true_cols) / float(maxi(true_rows, 1)), 1.0 / _MAX_ASPECT, _MAX_ASPECT)
	var w := _TARGET_SIZE
	var h := _TARGET_SIZE
	if aspect >= 1.0:
		h = _TARGET_SIZE / aspect
	else:
		w = _TARGET_SIZE * aspect
	var cw := w / float(cols)
	var ch := h / float(rows)

	# Build one vertex-colored mesh for the whole heatmap: two triangles per cell (one draw call).
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for r in rows:
		var row: Array = cells[r]
		for c in cols:
			var v := float(row[c])
			var col := _heat(v, accent)
			# Plane in XY, centered at origin; row 0 is at the top (+Y).
			var x0 := -w * 0.5 + float(c) * cw
			var x1 := x0 + cw * 0.92        # small gap → visible grid cells
			var y1 := h * 0.5 - float(r) * ch
			var y0 := y1 - ch * 0.92
			_quad(st, x0, x1, y0, y1, col)
	var mesh := st.commit()
	if mesh != null and mesh.get_surface_count() > 0:
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.material_override = _surface_material(glow)
		root.add_child(mi)
		if bool(spec.get("pulse", false)):
			var p := _Pulse.new(); p.mat = mi.material_override; p.g = maxf(glow, 0.6); root.add_child(p)

	var title := String(spec.get("title", ""))
	if title != "":
		var tl := ctx.make_label(title, 0.13, _color(spec.get("accent"), Color(0.7, 0.95, 1.0)))
		tl.position = Vector3(0, h * 0.5 + 0.22, 0.02)
		root.add_child(tl)
	if entity.label != "":
		var el := ctx.make_label(entity.label, 0.07, Color(0.8, 0.92, 1.0))
		el.position = Vector3(0, h * 0.5 + 0.1, 0.02)
		root.add_child(el)

	# Dimension label (always the TRUE dimensions, even when the grid is schematically downsampled).
	var dim_txt := "%d x %d" % [true_rows, true_cols]
	if note != "":
		dim_txt += "  ·  " + note
	if schematic:
		dim_txt += "  (schematic)"
	var label := ctx.make_label(dim_txt, 0.085, Color(0.78, 0.92, 1.0))
	label.position = Vector3(0, -h * 0.5 - 0.16, 0.02)
	root.add_child(label)
	var eq := ctx.eqn_sprite(String(spec.get("eqn", "")))
	if eq != null:
		eq.position = Vector3(0, -h * 0.5 - 0.42, 0.02)
		root.add_child(eq)

	return root


## Resolve the payload into a capped grid of normalized [0,1] values + the matrix's TRUE dimensions.
func _resolve_grid(spec: Dictionary) -> Dictionary:
	var values: Variant = spec.get("values")
	if values is Array and not (values as Array).is_empty() and (values as Array)[0] is Array:
		return _from_values(values, spec)

	# No values → schematic grid sized to the declared dimensions (honest: dims real, surface synthesized).
	var true_rows := int(spec.get("rows", 0))
	var true_cols := int(spec.get("cols", 0))
	if (true_rows <= 0 or true_cols <= 0) and bool(spec.get("square", false)):
		true_rows = 16
		true_cols = 16
	if true_rows <= 0:
		true_rows = 12
	if true_cols <= 0:
		true_cols = 12
	var rows := mini(true_rows, _MAX_SIDE)
	var cols := mini(true_cols, _MAX_SIDE)
	var cells: Array = []
	for r in rows:
		var row: Array = []
		for c in cols:
			row.append(_schematic_value(r, c, rows, cols))
		cells.append(row)
	return {"cells": cells, "rows": rows, "cols": cols, "schematic": true,
			"true_rows": true_rows, "true_cols": true_cols}


## Real values → block-averaged down to <= _MAX_SIDE per axis, then min-max normalized to [0,1].
func _from_values(values: Array, spec: Dictionary) -> Dictionary:
	var true_rows := values.size()
	var true_cols := 0
	for r in values:
		if r is Array:
			true_cols = maxi(true_cols, (r as Array).size())
	if true_cols == 0:
		return {"cells": [], "rows": 0, "cols": 0, "schematic": false,
				"true_rows": true_rows, "true_cols": 0}

	var rows := mini(true_rows, _MAX_SIDE)
	var cols := mini(true_cols, _MAX_SIDE)
	var raw: Array = []
	var vmin := INF
	var vmax := -INF
	for r in rows:
		var row: Array = []
		var sr0 := r * true_rows / rows
		var sr1 := maxi(sr0 + 1, (r + 1) * true_rows / rows)
		for c in cols:
			var sc0 := c * true_cols / cols
			var sc1 := maxi(sc0 + 1, (c + 1) * true_cols / cols)
			var sum := 0.0
			var n := 0
			for sr in range(sr0, mini(sr1, true_rows)):
				var src: Array = values[sr] if values[sr] is Array else []
				for sc in range(sc0, mini(sc1, src.size())):
					sum += float(src[sc])
					n += 1
			var avg := sum / float(n) if n > 0 else 0.0
			row.append(avg)
			vmin = minf(vmin, avg)
			vmax = maxf(vmax, avg)
		raw.append(row)

	if spec.has("vmin"):
		vmin = float(spec["vmin"])
	if spec.has("vmax"):
		vmax = float(spec["vmax"])
	var span := vmax - vmin
	if span < 0.000001:
		span = 1.0
	var cells: Array = []
	for r in rows:
		var src_row: Array = raw[r]
		var row: Array = []
		for c in cols:
			row.append(clampf((float(src_row[c]) - vmin) / span, 0.0, 1.0))
		cells.append(row)
	return {"cells": cells, "rows": rows, "cols": cols, "schematic": false,
			"true_rows": true_rows, "true_cols": true_cols}


## Deterministic, decorative cell value for schematic grids: a smooth low-frequency field + light hash
## jitter so the surface reads as a data matrix. It encodes NO real weights — only the dimensions are true.
func _schematic_value(r: int, c: int, rows: int, cols: int) -> float:
	var u := float(c) / float(maxi(cols - 1, 1))
	var v := float(r) / float(maxi(rows - 1, 1))
	var smooth := 0.5 + 0.5 * sin((u * 3.3 + v * 2.1) * PI)
	var jitter := float((r * 73856093) ^ (c * 19349663) & 255) / 255.0
	return clampf(0.35 + 0.5 * smooth + 0.15 * (jitter - 0.5), 0.0, 1.0)


## Holographic heatmap ramp: dark base → accent → bright accent as the normalized value rises.
func _heat(t: float, accent: Color) -> Color:
	t = clampf(t, 0.0, 1.0)
	var low := Color(0.04, 0.07, 0.16)
	var hi := accent.lerp(Color(1.0, 1.0, 1.0), 0.35)   # bright but not pure white (avoids bloom blowout)
	var col := low.lerp(hi, t)
	col.a = 0.3 + 0.45 * t
	return col


func _quad(st: SurfaceTool, x0: float, x1: float, y0: float, y1: float, col: Color) -> void:
	var a := Vector3(x0, y0, 0.0)
	var b := Vector3(x1, y0, 0.0)
	var c := Vector3(x1, y1, 0.0)
	var d := Vector3(x0, y1, 0.0)
	for p in [a, b, c, a, c, d]:
		st.set_color(col)
		st.add_vertex(p)


## Unlit, additive, vertex-colored material so the heatmap glows holographically (LP-006).
func _surface_material(glow: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.vertex_color_use_as_albedo = true
	m.albedo_color = Color(glow * 0.6, glow * 0.6, glow * 0.6, 1.0)
	m.cull_mode = BaseMaterial3D.CULL_DISABLED      # visible from both sides as the object rotates
	m.disable_receive_shadows = true
	return m


func _color(v: Variant, fallback: Color) -> Color:
	if v is Array and v.size() >= 3:
		return Color(float(v[0]), float(v[1]), float(v[2]))
	return fallback


## Gentle living-heatmap pulse so a head reads as active, not a static print.
class _Pulse:
	extends Node3D
	var mat: StandardMaterial3D
	var g: float = 1.0
	var t: float = 0.0
	func _process(delta: float) -> void:
		t += delta
		if mat != null:
			var k := g * (1.3 + 0.4 * sin(t * 2.2))
			mat.albedo_color = Color(k, k, k, 1.0)

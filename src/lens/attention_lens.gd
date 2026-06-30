class_name AttentionLens
extends Lens

## Lens for `attention` payloads — self-attention shown COMPUTING, not as a static box (LP-018).
## A scaled-dot-product head plays out left→right: token lane → Q·Kᵀ score grid → a moving softmax row
## (the current query attending over all keys) → value mixing → the output token brightening. The grid's
## DIMENSIONS are the real sequence length; the score VALUES are deterministic + illustrative (labelled),
## so a viewer never mistakes them for a model's real attention weights (LP-013/LP-016 honesty split).
##   payload.data = {
##     seq?: int, d_model?: int, n_heads?: int, head?: int,   # real, labelled
##     accent?:[r,g,b], glow?:f
##   }

const _MAX_SEQ := 12      # cap rendered tokens so a long context stays legible (true seq still labelled)
const _GRID := 2.0        # score-grid side, scene units


func payload_type() -> String:
	return "attention"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var accent := _color(spec.get("accent"), Color(0.45, 0.9, 1.0))
	var glow := float(spec.get("glow", 1.4))
	var true_seq := int(spec.get("seq", 8))
	var seq := mini(maxi(true_seq, 2), _MAX_SEQ)
	var d_model := int(spec.get("d_model", 0))
	var n_heads := int(spec.get("n_heads", 0))
	var head := int(spec.get("head", 0))

	var viz := AttentionViz.new()
	viz.name = "attention_viz"
	viz.setup(seq, accent, glow, ctx)
	var eq := ctx.eqn_sprite(String(spec.get("eqn", "")))
	if eq != null:
		eq.position = Vector3(0, -1.95, 0.02)
		viz.add_child(eq)
	return viz


func _color(v: Variant, fallback: Color) -> Color:
	if v is Array and v.size() >= 3:
		return Color(float(v[0]), float(v[1]), float(v[2]))
	return fallback


## The animated mechanism: query tokens (left), a seq×seq score heatmap (center), value tokens (right),
## and one output token (far right) that mixes values weighted by the current query's softmax row. A pulse
## sweeps query rows so you watch attention "work" continuously.
class AttentionViz:
	extends Node3D

	const _GRID := 2.0
	var _seq: int = 8
	var _accent: Color = Color(0.45, 0.9, 1.0)
	var _glow: float = 1.4
	var _ctx: Lens.Context = null
	var _scores: Array = []                 # seq×seq deterministic illustrative scores in [0,1]
	var _q_tokens: Array[MeshInstance3D] = []
	var _v_tokens: Array[MeshInstance3D] = []
	var _highlight: MeshInstance3D = null    # moving row band over the grid
	var _t: float = 0.0
	var _q_mat: Array[ShaderMaterial] = []
	var _v_mat: Array[ShaderMaterial] = []
	var _step: Label3D = null

	func setup(seq: int, accent: Color, glow: float, ctx: Lens.Context) -> void:
		_seq = seq
		_accent = accent
		_glow = glow
		_ctx = ctx
		_scores = _make_scores(seq)
		_build_grid()
		_build_tokens()
		_build_highlight()
		_build_text()

	func _build_text() -> void:
		var q := _ctx.make_label("Q", 0.12, Color(0.8, 1.0, 1.0)); q.position = Vector3(-_GRID * 0.5 - 0.45, _GRID * 0.5 + 0.25, 0); add_child(q)
		var v := _ctx.make_label("V", 0.12, Color(0.6, 1.0, 0.8)); v.position = Vector3(_GRID * 0.5 + 0.45, _GRID * 0.5 + 0.25, 0); add_child(v)
		var k := _ctx.make_label("scores = Q·Kᵀ", 0.1, Color(0.8, 0.92, 1.0)); k.position = Vector3(0, _GRID * 0.5 + 0.3, 0); add_child(k)
		_step = _ctx.make_label("", 0.1, Color(1.0, 0.9, 0.6)); _step.position = Vector3(0, -_GRID * 0.5 - 0.9, 0); add_child(_step)

	# Deterministic causal-ish pattern (lower-triangular, recency-weighted) → real dims, illustrative cells.
	func _make_scores(n: int) -> Array:
		var rows: Array = []
		for r in n:
			var row: Array = []
			var sum := 0.0
			for c in n:
				var w := 0.0
				if c <= r:
					w = 0.25 + 0.75 * (1.0 - float(r - c) / float(maxi(r, 1)))
					w += 0.2 * (1.0 if c == 0 else 0.0)   # mild attention sink on token 0
				row.append(w)
				sum += w
			for c in n:
				row[c] = row[c] / sum if sum > 0.0 else 0.0
			rows.append(row)
		return rows

	func _build_grid() -> void:
		var cell := _GRID / float(_seq)
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		for r in _seq:
			for c in _seq:
				var v := float((_scores[r] as Array)[c])
				var col := _heat(v)
				var x0 := -_GRID * 0.5 + c * cell
				var y1 := _GRID * 0.5 - r * cell
				_quad(st, x0, x0 + cell * 0.9, y1 - cell * 0.9, y1, col)
		var mi := MeshInstance3D.new()
		mi.mesh = st.commit()
		mi.material_override = _add_mat()
		add_child(mi)

	func _build_tokens() -> void:
		var cell := _GRID / float(_seq)
		for i in _seq:
			var y := _GRID * 0.5 - (i + 0.5) * cell
			var q := _box(Vector3(0.16, cell * 0.7, 0.16), _accent)
			q.position = Vector3(-_GRID * 0.5 - 0.45, y, 0)
			add_child(q); _q_tokens.append(q); _q_mat.append(q.material_override)
			var vtok := _box(Vector3(0.16, cell * 0.7, 0.16), Color(0.5, 0.95, 0.75))
			vtok.position = Vector3(_GRID * 0.5 + 0.45, y, 0)
			add_child(vtok); _v_tokens.append(vtok); _v_mat.append(vtok.material_override)

	func _build_highlight() -> void:
		var cell := _GRID / float(_seq)
		_highlight = _box(Vector3(_GRID + 0.05, cell, 0.02), Color(1, 1, 1))
		add_child(_highlight)

	func _process(delta: float) -> void:
		_t += delta * 0.16
		var q := int(_t) % _seq
		var frac: float = _t - floor(_t)
		var cell := _GRID / float(_seq)
		# Move the highlight to the current query row.
		_highlight.position = Vector3(0, _GRID * 0.5 - (q + 0.5) * cell, 0.03)
		# Pulse query token; brighten value tokens by their softmax weight; build the output.
		for i in _seq:
			_q_mat[i].set_shader_parameter("selected", 1.0 if i == q else 0.0)
			var w := float((_scores[q] as Array)[i])
			_v_mat[i].set_shader_parameter("glow", 0.8 + 3.0 * w * frac)

	func _box(size: Vector3, tint: Color) -> MeshInstance3D:
		var mi := MeshInstance3D.new()
		var b := BoxMesh.new(); b.size = size
		mi.mesh = b
		mi.material_override = _ctx.holo_material(tint, _glow)
		return mi

	func _add_mat() -> StandardMaterial3D:
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.vertex_color_use_as_albedo = true
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		return m

	func _heat(t: float) -> Color:
		t = clampf(t, 0.0, 1.0)
		var col := Color(0.04, 0.07, 0.16).lerp(_accent, minf(t / 0.6, 1.0))
		col.a = 0.3 + 0.6 * t
		return col

	func _quad(st: SurfaceTool, x0: float, x1: float, y0: float, y1: float, col: Color) -> void:
		for p in [Vector3(x0,y0,0), Vector3(x1,y0,0), Vector3(x1,y1,0), Vector3(x0,y0,0), Vector3(x1,y1,0), Vector3(x0,y1,0)]:
			st.set_color(col); st.add_vertex(p)

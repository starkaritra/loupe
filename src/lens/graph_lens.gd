class_name GraphLens
extends Lens

## Lens for `graph` payloads — nodes + edges in 3D. The most universal data lens (data-contract.md):
## serves PDB atoms+bonds, connectomes, molecules, code/dependency graphs, circuits, pathways.
##   payload.data = {
##     nodes: [ {pos:[x,y,z], color?:[r,g,b], r?:float, label?:str}, ... ],
##     edges: [ [i, j], ... ],                      # indices into nodes
##     node_color?:[r,g,b], edge_color?:[r,g,b], node_radius?:float, glow?:float
##   }
## Node positions are used as-is when present (e.g. real atomic coordinates); the lens auto-centers and
## scales the whole cloud to a consistent on-screen size so any source fits the scene.

const _TARGET_SIZE := 3.0
const _MAX_NODES := 4000   # safety cap so a huge graph doesn't stall the build


func payload_type() -> String:
	return "graph"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var root := Node3D.new()
	root.name = "graph_visual"
	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var nodes: Array = spec.get("nodes", [])
	if nodes.is_empty():
		return root

	var node_color := _color(spec.get("node_color"), Color(0.55, 0.85, 1.0))
	var edge_color := _color(spec.get("edge_color"), Color(0.4, 0.7, 1.0, 0.6))
	var node_radius := float(spec.get("node_radius", 0.05))
	var glow := float(spec.get("glow", 1.3))

	# Positions → centered + scaled to a consistent size.
	var positions: Array[Vector3] = []
	for n in nodes:
		positions.append(_node_pos(n))
	var xform := Transform3D.IDENTITY if bool(spec.get("raw", false)) else _fit_transform(positions)

	# Nodes via MultiMesh (one draw call for thousands of atoms).
	var count := mini(nodes.size(), _MAX_NODES)
	var sphere := SphereMesh.new()
	sphere.radius = node_radius
	sphere.height = node_radius * 2.0
	sphere.radial_segments = 8
	sphere.rings = 4
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = sphere
	mm.instance_count = count
	for i in count:
		var p: Vector3 = xform * positions[i]
		mm.set_instance_transform(i, Transform3D(Basis(), p))
		mm.set_instance_color(i, _color((nodes[i] as Dictionary).get("color") if nodes[i] is Dictionary else null, node_color))
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	var node_mat := ctx.holo_material(node_color, glow)
	node_mat.set_shader_parameter("base_alpha", 0.5)
	mmi.material_override = node_mat
	root.add_child(mmi)

	# Edges via a single line mesh.
	var edges: Array = spec.get("edges", [])
	if not edges.is_empty():
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_LINES)
		for e in edges:
			if e is Array and e.size() == 2:
				var a := int(e[0])
				var b := int(e[1])
				if a >= 0 and a < positions.size() and b >= 0 and b < positions.size():
					st.set_color(edge_color)
					st.add_vertex(xform * positions[a])
					st.set_color(edge_color)
					st.add_vertex(xform * positions[b])
		var line_mesh := st.commit()
		if line_mesh != null and line_mesh.get_surface_count() > 0:
			var lines := MeshInstance3D.new()
			lines.mesh = line_mesh
			lines.material_override = ctx.line_material(edge_color)
			root.add_child(lines)

	return root


func _node_pos(n: Variant) -> Vector3:
	if n is Dictionary and n.get("pos") is Array and (n["pos"] as Array).size() == 3:
		var p: Array = n["pos"]
		return Vector3(float(p[0]), float(p[1]), float(p[2]))
	return Vector3.ZERO


## Center the point cloud at origin and scale its longest extent to _TARGET_SIZE.
func _fit_transform(positions: Array[Vector3]) -> Transform3D:
	if positions.is_empty():
		return Transform3D.IDENTITY
	var mn := positions[0]
	var mx := positions[0]
	for p in positions:
		mn = Vector3(minf(mn.x, p.x), minf(mn.y, p.y), minf(mn.z, p.z))
		mx = Vector3(maxf(mx.x, p.x), maxf(mx.y, p.y), maxf(mx.z, p.z))
	var center := (mn + mx) * 0.5
	var extent := (mx - mn)
	var longest := maxf(extent.x, maxf(extent.y, extent.z))
	var s := _TARGET_SIZE / longest if longest > 0.0001 else 1.0
	return Transform3D(Basis().scaled(Vector3(s, s, s)), -center * s)


func _color(v: Variant, fallback: Color) -> Color:
	if v is Array and v.size() >= 3:
		var a := float(v[3]) if v.size() >= 4 else 1.0
		return Color(float(v[0]), float(v[1]), float(v[2]), a)
	return fallback

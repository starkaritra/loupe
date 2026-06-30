class_name ProcMesh
extends RefCounted

## Generic procedural geometry for mechanical/CAD-style parts (LP-011). Surfaces of revolution and swept
## tubes are what make a part read as "real" (a rocket bell nozzle, a combustion chamber, a propellant
## line) while staying completely domain-agnostic — the rocket-specific math lives in the ingestor, not
## here. All builders return an ArrayMesh with generated normals.


## Surface of revolution: revolve a 2D silhouette around the Y axis.
## profile: Array of [radius, y] (or Vector2). segments: angular subdivisions.
static func revolve(profile: Array, segments: int = 48) -> ArrayMesh:
	var pts: Array[Vector2] = _to_vec2(profile)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	if pts.size() < 2 or segments < 3:
		return st.commit()

	for i in pts.size() - 1:
		var a: Vector2 = pts[i]        # (r, y) lower
		var b: Vector2 = pts[i + 1]    # (r, y) upper
		for j in segments:
			var t0 := float(j) / float(segments) * TAU
			var t1 := float(j + 1) / float(segments) * TAU
			var c0 := Vector2(cos(t0), sin(t0))
			var c1 := Vector2(cos(t1), sin(t1))
			var a0 := Vector3(a.x * c0.x, a.y, a.x * c0.y)
			var a1 := Vector3(a.x * c1.x, a.y, a.x * c1.y)
			var b0 := Vector3(b.x * c0.x, b.y, b.x * c0.y)
			var b1 := Vector3(b.x * c1.x, b.y, b.x * c1.y)
			# Two triangles per quad (skip degenerate edges at r≈0 apexes).
			if a.x > 0.0001:
				_tri(st, a0, b0, a1)
			if b.x > 0.0001:
				_tri(st, a1, b0, b1)
	st.generate_normals()
	return st.commit()


## Swept tube along a polyline path with a circular cross-section. Good for plumbing / propellant lines.
## path: Array of [x,y,z] (or Vector3). radius: tube radius. sides: cross-section resolution.
static func tube(path: Array, radius: float = 0.08, sides: int = 12) -> ArrayMesh:
	var pts: Array[Vector3] = _to_vec3(path)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	if pts.size() < 2 or sides < 3:
		return st.commit()

	var rings: Array = []
	var up := Vector3.UP
	for i in pts.size():
		var tangent: Vector3
		if i == 0:
			tangent = (pts[1] - pts[0])
		elif i == pts.size() - 1:
			tangent = (pts[i] - pts[i - 1])
		else:
			tangent = (pts[i + 1] - pts[i - 1])
		tangent = tangent.normalized()
		if absf(tangent.dot(up)) > 0.99:
			up = Vector3.RIGHT
		var n1 := tangent.cross(up).normalized()
		var n2 := tangent.cross(n1).normalized()
		var ring: Array[Vector3] = []
		for s in sides:
			var ang := float(s) / float(sides) * TAU
			ring.append(pts[i] + (n1 * cos(ang) + n2 * sin(ang)) * radius)
		rings.append(ring)

	for i in rings.size() - 1:
		var r0: Array = rings[i]
		var r1: Array = rings[i + 1]
		for s in sides:
			var s2 := (s + 1) % sides
			_tri(st, r0[s], r1[s], r0[s2])
			_tri(st, r0[s2], r1[s], r1[s2])
	st.generate_normals()
	return st.commit()


static func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3) -> void:
	st.add_vertex(a)
	st.add_vertex(b)
	st.add_vertex(c)


static func _to_vec2(arr: Array) -> Array[Vector2]:
	var out: Array[Vector2] = []
	for v in arr:
		if v is Vector2:
			out.append(v)
		elif v is Array and v.size() >= 2:
			out.append(Vector2(float(v[0]), float(v[1])))
	return out


static func _to_vec3(arr: Array) -> Array[Vector3]:
	var out: Array[Vector3] = []
	for v in arr:
		if v is Vector3:
			out.append(v)
		elif v is Array and v.size() >= 3:
			out.append(Vector3(float(v[0]), float(v[1]), float(v[2])))
	return out

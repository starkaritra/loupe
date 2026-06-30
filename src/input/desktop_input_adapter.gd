class_name DesktopInputAdapter
extends Node

## The first input adapter (LP-008): translates desktop mouse/keyboard into device-agnostic intents on
## the IntentBus. It owns NO scene state and makes NO direct changes to the object — it only emits intents.
## A future XR adapter will emit the same intents from controllers/hands without touching the Stage.

@export var rotate_sensitivity: float = 0.01
@export var pan_sensitivity: float = 0.012
@export var zoom_step: float = 1.0
@export var explode_step: float = 0.12

var _dragging: bool = false
var _panning: bool = false
var _press_pos: Vector2 = Vector2.ZERO
var _moved: float = 0.0


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		_on_mouse_button(event)
	elif event is InputEventMouseMotion:
		if _dragging:
			_moved += event.relative.length()
			IntentBus.emit_intent(Intent.Kind.ROTATE, {"delta": event.relative * rotate_sensitivity})
		elif _panning:
			IntentBus.emit_intent(Intent.Kind.PAN, {"delta": event.relative * pan_sensitivity})
	elif event is InputEventKey and event.pressed and not event.echo:
		_on_key(event)


func _on_mouse_button(event: InputEventMouseButton) -> void:
	match event.button_index:
		MOUSE_BUTTON_LEFT:
			_dragging = event.pressed
			if event.pressed:
				_press_pos = event.position
				_moved = 0.0
				IntentBus.emit_intent(Intent.Kind.GRAB)
			else:
				IntentBus.emit_intent(Intent.Kind.RELEASE)
				# A click that didn't drag = a pick: ask the Stage to inspect what's under the cursor.
				if _moved < 6.0:
					IntentBus.emit_intent(Intent.Kind.INSPECT, {"screen": event.position})
		MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE:
			_panning = event.pressed
		MOUSE_BUTTON_WHEEL_UP:
			if event.pressed:
				IntentBus.emit_intent(Intent.Kind.ZOOM, {"amount": zoom_step})
		MOUSE_BUTTON_WHEEL_DOWN:
			if event.pressed:
				IntentBus.emit_intent(Intent.Kind.ZOOM, {"amount": -zoom_step})


func _on_key(event: InputEventKey) -> void:
	match event.keycode:
		KEY_E:
			IntentBus.emit_intent(Intent.Kind.EXPLODE, {"amount": explode_step})
		KEY_Q:
			IntentBus.emit_intent(Intent.Kind.COLLAPSE, {"amount": explode_step})

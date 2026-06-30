extends Node

## Autoload singleton (registered as `IntentBus` in project.godot).
## The one decoupling seam between input devices and the Stage. Input adapters call `emit_intent(...)`;
## the Stage connects to `intent`. This is what makes XR "just another adapter" (LP-007), so it must stay
## device-agnostic — never reference mouse/keyboard/XR specifics here.

## kind: Intent.Kind ; args: Dictionary payload (see Intent enum docs for per-kind args)
signal intent(kind: int, args: Dictionary)

func emit_intent(kind: int, args: Dictionary = {}) -> void:
	intent.emit(kind, args)

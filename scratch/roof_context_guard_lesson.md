Decision: For localized architectural repairs where a raw OpenAI donor looks visually best but can distort adjacent repeated structure, use the raw donor as a visual target only and build the final image with separate final-blend masks plus explicit protected-zone gates.

Reason: In Berlin wave7 hotel-roof repair, the raw precise donor had the best top-building architecture, but it changed 227064 pixels in the upper-floor guard and would have distorted the window/floor rhythm. The accepted working pattern was to keep the donor's roof/parapet pixels while restoring or guarding the original top floors, then verify `floor_guard_changed_vs_pre_roof=0` and `stair_protected_changed_vs_pre_roof=0` on actual composites such as `v11_right_parapet_precise_reinforced.png`.

Procedure:
1. Use a broad generation/context mask when the model needs architectural context.
2. Treat the raw output as a donor/reference, not a final composite.
3. Build a separate final blend mask that excludes preserved repeated structures such as windows/floors.
4. Add explicit guard regions for preserved structures and already-approved repairs.
5. Show a context board that includes both the defect and the preserved adjacent structure, because tight crops can hide floor/window distortion.

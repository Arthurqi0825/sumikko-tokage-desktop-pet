# Tokage look mechanics

Tokage is a soft, pear-shaped dinosaur with no separate neck. The lower belly and feet form the stable ground anchor. Direction changes should be led by the dot eyes and tiny snout, followed by a restrained turn, bend, or squash of the upper third of the body. The lower body stays registered; the whole sprite must not rotate or rock.

The eyes are flat drawn features on the face surface, so they may shift subtly with the face but must remain tiny brown dots. Preserve the original wavy mouth, cream belly, powder-blue body, brown outline, and small dorsal plates. There are no props.

Motion budget: each 22.5-degree step advances the face, upper-body bend, and visible dorsal-plate side by a similar small amount. Body height and baseline remain stable except for a slight upward stretch near 000 and slight squash near 180. No adjacent pose may jump, flip, or change scale.

## Cardinal pose families

- **000 up:** lower body anchored; upper body stretches slightly upward; dot eyes and snout clearly aim toward the top edge; eyelids open; dorsal plates remain attached and follow the upper-body lift.
- **090 screen-right:** face and upper body yaw toward the viewer's right; nose tip and both eye cues sit right of the head center; more of the left/rear body contour is visible and the dorsal plates read along the rear edge.
- **180 down:** lower body anchored; upper body gently bows and squashes; eyes, eyelids, and snout clearly aim toward the belly/bottom edge; dorsal plates compress with the body without changing identity.
- **270 screen-left:** face and upper body yaw toward the viewer's left; nose tip and both eye cues sit left of the head center; the opposite/rear contour becomes visible and the dorsal plates remain attached along the rear edge.

Diagonals interpolate between these families. The 337.5 pose must land one even step before 000, and the 157.5 pose one even step before 180. No cardinal may read as neutral/front-facing.


/** Idle-loop parameter follow. A raw lerp across a 0–1 wrap yanks the packet backward. */
export function followU(current, target, k) {
  if (!Number.isFinite(current)) current = 0;
  if (!Number.isFinite(target)) target = 0;
  if (target + 0.45 < current) return target;
  return current + (target - current) * k;
}

/** WebGL canvases jitter when CSS left/top are fractional pixels. */
export function snapBox(left, top, width, height) {
  return {
    left: Math.round(left),
    top: Math.round(top),
    width: Math.max(0, Math.round(width)),
    height: Math.max(0, Math.round(height)),
  };
}

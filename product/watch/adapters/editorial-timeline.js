import { sourceToOutputTime } from "./catalog.js";

// Chapters use source seconds; the player uses the published movie's own clock.
export function presentationTimeForSource(match, second, step = 0) {
  const freeze = match.production.timeline.find(
    (segment) =>
      segment.kind === "freeze" &&
      Math.abs(segment.sourceStart - second) < 0.02,
  );
  if (!freeze)
    return sourceToOutputTime({ ...match, enhancedAvailable: true }, second);
  const reading = Math.max(0, Math.min(2, Math.floor(Number(step) || 0)));
  return (
    freeze.outputStart + 0.4 + reading * match.production.readingStepSeconds
  );
}

export function reviewAt(match, outputSecond) {
  const freeze = match.production.timeline.find(
    (segment) =>
      segment.kind === "freeze" &&
      outputSecond >= segment.outputStart &&
      outputSecond < segment.outputEnd,
  );
  return freeze
    ? {
        scene: freeze.scene,
        step: Math.min(
          2,
          Math.floor(
            (outputSecond - freeze.outputStart + 1e-9) /
              match.production.readingStepSeconds,
          ),
        ),
      }
    : null;
}

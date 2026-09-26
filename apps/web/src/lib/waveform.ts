// Fixed-work visual approximation, not a peak meter or analysis input.
export function sampledWaveform(channels: ArrayLike<number>[]): string {
  const length = channels[0]?.length ?? 0;
  if (!length) return '';
  const bins = Math.min(1200, length);
  const upper: string[] = [], lower: string[] = [];
  for (let bin = 0; bin < bins; bin++) {
    const start = Math.floor(bin * length / bins);
    const end = Math.floor((bin + 1) * length / bins);
    const count = Math.min(64, end - start);
    let peak = 0;
    for (const channel of channels.slice(0, 2)) {
      for (let sample = 0; sample < count; sample++) {
        const value = channel[start + Math.floor(sample * (end - start) / count)];
        if (Number.isFinite(value)) peak = Math.max(peak, Math.abs(value));
      }
    }
    const x = (bin / bins * 1000).toFixed(2), height = Math.min(1, peak) * 28;
    upper.push(`${x},${(57 - height).toFixed(2)}`);
    lower.push(`${x},${(57 + height).toFixed(2)}`);
  }
  return [...upper, ...lower.reverse()].join(' ');
}

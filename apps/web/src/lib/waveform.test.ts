import { expect, test } from 'bun:test';
import { sampledWaveform } from './waveform';

test('waveform work stays bounded for long stereo recordings', () => {
  let reads = 0;
  const target: { length: number; [index: number]: number } = { length: 200_000_000 };
  const channel = new Proxy(target, {
    get(target, property) {
      if (property === 'length') return target.length;
      reads++;
      return 0.5;
    },
  });
  const points = sampledWaveform([channel, channel, channel]).split(' ');
  expect(reads).toBe(1200 * 64 * 2);
  expect(points.length).toBe(2400);
  expect(points[0]).toBe('0.00,43.00');
  expect(points.at(-1)).toBe('0.00,71.00');
});

test('empty, short, and invalid samples remain finite', () => {
  expect(sampledWaveform([])).toBe('');
  expect(sampledWaveform([new Float32Array([NaN, Infinity, -2])])).not.toMatch(/NaN|Infinity/);
  expect(sampledWaveform([new Float32Array([0])])).toBe('0.00,57.00 0.00,57.00');
});

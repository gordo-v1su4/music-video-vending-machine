import type { Section, TranscriptionJob } from './api';

type Transcript = NonNullable<TranscriptionJob['result']>;

/** Half-open song ranges: a word belongs to exactly one section, by its onset. */
export function sectionLyrics(section: Pick<Section, 'startMs' | 'endMs'>, transcript: Transcript | null | undefined) {
  const words = (transcript?.words ?? []).filter(w => w.startMs >= section.startMs && w.startMs < section.endMs);
  return {
    text: words.map(w => w.text).join(' '),
    startMs: words[0]?.startMs,
    endMs: words.at(-1)?.endMs,
    needsReview: words.some(w => w.confidence == null || w.confidence < 0.75),
  };
}

/** Some lyric exports include service metadata and old audio URLs. Import wording only. */
export function extractLyricReference(text: string) {
  const marker = '--- Lyrics ---';
  const lyrics = text.includes(marker) ? text.slice(text.indexOf(marker) + marker.length).split('Cover Art URL:')[0] : text;
  return lyrics.trim();
}

import { test, expect } from 'bun:test';
import { sectionLyrics, extractLyricReference } from './section-lyrics';
import type { TranscriptionJob } from './api';

test('words crossing a boundary stay with their onset; exact boundary starts next card', () => {
  const transcript: NonNullable<TranscriptionJob['result']> = { model:'fixture', durationMs:3000, transcript:'Stay here', wordCount:2, chunks:[], words:[{startMs:900,endMs:1100,text:'Stay',confidence:0.9},{startMs:1000,endMs:1300,text:'here',confidence:0.5}],summary:'',topics:[],intents:[],warnings:[] };
  expect(sectionLyrics({startMs:0,endMs:1000},transcript).text).toBe('Stay');
  expect(sectionLyrics({startMs:1000,endMs:2000},transcript)).toMatchObject({text:'here',needsReview:true});
  expect(sectionLyrics({startMs:2000,endMs:3000},transcript).text).toBe('');
  expect(sectionLyrics({startMs:0,endMs:1000},null).text).toBe('');
});

test('reference import excludes unrelated export metadata and URLs', () => {
  expect(extractLyricReference('Duration: 12\n--- Lyrics ---\nWords to keep\n\nCover Art URL: https://example.test\nraw payload')).toBe('Words to keep');
  expect(extractLyricReference('  Plain lyrics\nsecond line  ')).toBe('Plain lyrics\nsecond line');
});

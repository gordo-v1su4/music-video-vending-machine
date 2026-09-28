import { test, expect } from 'bun:test';
import { assignmentsFromPlan, lookPlanProblems, lookReadiness, planFromAssignments, sectionLooks, type Character } from './looks';

const coat = { id: 'coat', name: 'Grey coat', hair: 'Short black', costume: 'Grey coat', sheetReferenceIds: ['exact'], approved: true };
const dress = { id: 'dress', name: 'Blue dress', hair: 'Short black', costume: 'Blue dress', sheetReferenceIds: [], approved: false };
const traveller: Character = { id: 'traveller', name: 'Traveller', description: '', looks: [coat, dress] };
const sections = [
  { id: 'a', name: 'Arrival', startMs: 0, endMs: 1000, intent: '' },
  { id: 'b', name: 'Return', startMs: 1000, endMs: 2000, intent: '' },
];

test('plan round-trips and records empty sections explicitly', () => {
  const project = { characters: [traveller], lookAssignments: [{ sectionId: 'a', lookIds: ['coat'] }] };
  const plan = planFromAssignments(project);
  expect(plan).toEqual({ a: { traveller: 'coat' } });
  expect(assignmentsFromPlan(plan, ['a', 'b'])).toEqual([
    { sectionId: 'a', lookIds: ['coat'] },
    { sectionId: 'b', lookIds: [] },
  ]);
});

test('problems mirror production approval rules', () => {
  expect(lookPlanProblems({ sections, characters: [], lookAssignments: [] })).toEqual([]);
  expect(lookPlanProblems({ sections, characters: [traveller], lookAssignments: [{ sectionId: 'a', lookIds: ['dress'] }] }))
    .toEqual(['1 section needs a saved Look plan.', '1 assigned Look needs approval.']);
  expect(lookPlanProblems({ sections, characters: [traveller], lookAssignments: [
    { sectionId: 'a', lookIds: ['coat'] }, { sectionId: 'b', lookIds: [] },
  ] })).toEqual([]);
});

test('section looks distinguish unplanned from intentionally empty', () => {
  const project = { characters: [traveller], lookAssignments: [{ sectionId: 'a', lookIds: ['coat'] }, { sectionId: 'b', lookIds: [] }] };
  expect(sectionLooks(project, 'a')?.map((x) => x.look.name)).toEqual(['Grey coat']);
  expect(sectionLooks(project, 'b')).toEqual([]);
  expect(sectionLooks(project, 'c')).toBeNull();
});

test('readiness requires hair, costume and an exact sheet reference', () => {
  const references = [
    { id: 'exact', assetId: 'x', name: 'Face', role: 'exact' as const, description: '' },
    { id: 'mood', assetId: 'y', name: 'Mood', role: 'inspiration' as const, description: '' },
  ];
  expect(lookReadiness(coat, references)).toBeNull();
  expect(lookReadiness({ ...coat, sheetReferenceIds: ['mood'] }, references)).toContain('exact-constraint');
  expect(lookReadiness({ ...coat, costume: ' ' }, references)).toContain('hair and costume');
});

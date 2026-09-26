/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as analysis from "../analysis.js";
import type * as analysisWorker from "../analysisWorker.js";
import type * as assets from "../assets.js";
import type * as maintenance from "../maintenance.js";
import type * as migration from "../migration.js";
import type * as projects from "../projects.js";
import type * as sessions from "../sessions.js";
import type * as transcription from "../transcription.js";
import type * as transcriptionWorker from "../transcriptionWorker.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  analysis: typeof analysis;
  analysisWorker: typeof analysisWorker;
  assets: typeof assets;
  maintenance: typeof maintenance;
  migration: typeof migration;
  projects: typeof projects;
  sessions: typeof sessions;
  transcription: typeof transcription;
  transcriptionWorker: typeof transcriptionWorker;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {};

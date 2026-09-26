# Bootstrap API contract

All endpoints under /api/v1. JSON camelCase. The operator bootstrap key authorizes only POST /sessions; project and media endpoints require the resulting session bearer token. Neither credential belongs in browser storage or URLs. Development may explicitly enable loopback-only unauthenticated mode. No implicit auth bypass when deployed.

- POST /sessions: bootstrap bearer plus {clientLabel}; returns {token,session:{id,clientLabel,createdAt,expiresAt}} (201). Fixed 12-hour expiry; database stores SHA-256 token and issuer hashes only.
- GET /sessions/current: current session metadata, or null in anonymous development.
- POST /sessions/current/revoke: revoke the calling session.
- POST /sessions/revoke-all: revoke sessions issued by the current bootstrap key, including the caller.
- Rotation of the bootstrap key invalidates existing sessions. Reverting that key can re-enable unexpired sessions unless they were explicitly revoked first.
- SSE checks session validity each second and ends with a session-ended event. Writes recheck after body extraction (and project-lock acquisition); an already-authorized storage operation may finish after sign-out. Its durable receipt remains recoverable.
- The UI holds credentials only in memory, polls remote revocation every 15 seconds, and schedules an authoritative server check using the session duration and a monotonic timer. Client wall-clock skew cannot discard a token before remote sign-out. Unsaved drafts stay in the current window across sign-out/reconnect; closing or reloading loses them. Failed remote sign-out remains visible and retryable. Failed replacement connections preserve the working session, and a successful poll clears a transient session-check error.
- Hourly cleanup removes at most 1,000 session rows that expired or were revoked more than seven days ago. Active and recently ended sessions remain available; expiry and revocation indexes support bounded cleanup.

- GET /health: {status, storage, version, development, sessionRequired, capabilities}; readiness must fail on unavailable database.
- GET /projects: Project[] summaries or full projects.
- POST /projects: {name}; returns Project (201).
- GET /projects/:id: Project.
- POST /projects/:id/actions: {expectedRevision, action}; returns updated Project, 409 on stale revision, 422 on invalid action, 404 unknown project.
- GET /projects/:id/events?after=N: durable resumable events (SSE).

Project: {id,name,revision,master:null|{assetId,durationMs,approved},treatment,sections:Section[],references:Reference[],breaks:AudioBreak[],shots:Shot[],revisions:EditRevision[],activeRevisionId:null|string,productionApproval:null|{fingerprint,localAttemptsPerShot},createdAt,updatedAt}.
Section: {id,name,startMs,endMs,intent}. Reference: {id,assetId,name,role:'exact'|'inspiration',description}.
AudioBreak: {id,kind:'insertion'|'cutout',songStartMs,durationMs,assetId:null|string}.
Shot: {id,sectionId,startMs,endMs,intent,pinned,candidateAssetId:null|string,status:'gap'|'candidate'|'accepted',attempts}.
EditRevision: {id,label,parentId:null|string,status:'candidate'|'active'|'rejected'|'archived',shots:Shot[]}.

Actions use discriminated type:
- {type:'setTreatment',text}
- {type:'setMaster',assetId,durationMs} (server verifies asset metadata; approval false)
- {type:'approveMaster'}
- {type:'setSections',sections}
- {type:'addReference',reference}
- {type:'setBreaks',breaks}
- {type:'approveProduction',localAttemptsPerShot:3}
- {type:'setShots',shots} (approval required; user edits preserve pins)
- {type:'pinShot',shotId,pinned}
- {type:'createRevision',label,shots} (candidate; preserve active pins)
- {type:'keepRevision',revisionId}
- {type:'rejectRevision',revisionId}
- {type:'restoreRevision',revisionId} (restoration creates a new candidate)

Assets: POST /projects/:id/assets multipart file; return {id,projectId,name,mediaType,sha256,sizeBytes,durationMs,url}. GET /projects/:id/assets lists assets. URL is authenticated coordinator asset endpoint; frontend fetches blob with authorization. Never trust client-reported audio duration.

Implementation stages must not expose unimplemented generation/export as successful. UI renders capability/errors honestly and uses real persisted API state rather than a fabricated default project.

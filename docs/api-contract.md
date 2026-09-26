# Bootstrap API contract

All endpoints under /api/v1. JSON camelCase. Protected endpoints accept an operator bearer token; never persist it in browser storage. Development may explicitly enable loopback-only unauthenticated mode. No implicit auth bypass when deployed.

- GET /health: {status, storage, version}; readiness must fail on unavailable database.
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

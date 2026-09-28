// The locally assembled pilot cut (scripts/mvvm_gen/review_server.py, /pilot-api/cut): where it sits in
// the song and each shot's span. Shared by the Review tab and the Preview panel.
export type CutShot = {
  id: string;
  summary: string;
  startMs: number;
  endMs: number;
  take: number;
  pickNow: number;
  source: string;
};
export type CutInfo =
  | { exists: false; plan: string }
  | {
      exists: true;
      plan: string;
      url: string;
      songStartMs: number;
      durationMs: number;
      builtAt: string | null;
      shots: CutShot[];
      stale: boolean;
    };

class PilotCut {
  info = $state<CutInfo | null>(null);
  loading = $state(false);
  building = $state(false);
  error = $state("");
  unavailable = $state(false);

  async load() {
    this.loading = true;
    try {
      const res = await fetch("/pilot-api/cut");
      if (!res.ok) throw new Error(String(res.status));
      this.info = await res.json();
      this.unavailable = false;
    } catch {
      this.unavailable = true;
    } finally {
      this.loading = false;
    }
  }

  async build() {
    if (this.building) return;
    this.building = true;
    this.error = "";
    try {
      const res = await fetch("/pilot-api/cut/build", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "The cut could not be built.");
      this.info = data;
    } catch (e) {
      this.error = e instanceof Error ? e.message : "The cut could not be built.";
    } finally {
      this.building = false;
    }
  }
}

export const pilotCut = new PilotCut();

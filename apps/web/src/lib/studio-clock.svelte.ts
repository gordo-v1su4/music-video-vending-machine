// One studio playhead. The Transport owns playback and publishes song time here; other views
// (the song map, section lists) read it and ask the Transport to seek or play instead of playing audio themselves.
type Controls = { seekSong: (songMs: number) => void; play: () => void; pause: () => void };

class StudioClock {
  songMs = $state(0);
  playing = $state(false);
  available = $state(false);
  #controls: Controls | null = null;

  attach(controls: Controls) {
    this.#controls = controls;
    this.available = true;
    return () => {
      if (this.#controls === controls) {
        this.#controls = null;
        this.available = false;
        this.playing = false;
      }
    };
  }

  seek(songMs: number) {
    this.#controls?.seekSong(Math.max(0, songMs));
  }

  playFrom(songMs: number) {
    this.seek(songMs);
    this.#controls?.play();
  }

  toggle() {
    if (this.playing) this.#controls?.pause();
    else this.#controls?.play();
  }
}

export const studioClock = new StudioClock();

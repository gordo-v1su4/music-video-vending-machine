<script lang="ts">
  export type IconName =
    | "story"
    | "image"
    | "production"
    | "review"
    | "settings"
    | "close"
    | "arrow"
    | "audio"
    | "play"
    | "pause"
    | "upload";
  let { name, size = 20 }: { name: IconName; size?: number } = $props();
  const paths: Record<IconName, string> = {
    story: "M5 4h14v16H5z M8 8h8 M8 12h8 M8 16h5",
    image: "M3 4h18v16H3z M3 16l6-6 5 5 3-3 4 4 M16 8h.01",
    production: "M4 7h16v14H4z M4 7l-1-4 17-2 1 4z M8 2l3 4 M14 2l3 3",
    review:
      "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M9 12a3 3 0 1 0 6 0 3 3 0 1 0-6 0",
    settings: "M4 7h16 M4 17h16 M9 4v6 M16 14v6",
    close: "M6 6l12 12 M18 6 6 18",
    arrow: "M5 19 19 5 M7 5h12v12",
    audio:
      "M9 18V5l11-2v13 M9 18c0 4-6 4-6 1s6-4 6-1 M20 16c0 4-6 4-6 1s6-4 6-1",
    play: "M7 4l14 8-14 8z",
    pause: "M8 4v16 M16 4v16",
    upload: "M12 16V3 M7 8l5-5 5 5 M4 16v5h16v-5",
  };
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.6"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  focusable="false"><path d={paths[name]} /></svg
>

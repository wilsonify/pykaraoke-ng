import { makeCallApi } from './bridge.js';

export const STORAGE_KEY = 'pykaraoke-ng:state';
export const QUEUE_KEY = 'pykaraoke-ng:queue';

export function createStore(tauriCore) {
  const callApi = makeCallApi(tauriCore);
  const $ = (id) => document.getElementById(id);

  const state = {
    queue: new (require('./helpers.js').SongQueue)(),
    settings: { volume: 0.75, sort: 'filename', zoom: 'int', lookInsideZips: true },
    files: new Map(),
    pathByBase: new Map(),
    results: [],
    selectedResult: -1,
    current: null,
    playing: false,
    durationMs: 0,
    lyricLines: null,
    parts: null,
    lastLyricLine: -1,
    cdgKey: null,
    audioEl: null,
    videoEl: null,
    synth: null,
    songClock: 0,
    rafId: null,
    frameFn: null,
    callApi,
    $,
    tauriCore,
  };

  return state;
}

// Local voice transport: microphone -> 16 kHz PCM -> WebSocket (the server finds the end of the answer and
// transcribes it); Pythagoras's lines come back as WAV chunks, one per sentence, and are played gaplessly.
// Half-duplex: the microphone is closed while Pythagoras speaks, so there is no echo even without headphones.
class LocalVoice {
  constructor(token, handlers) {
    this.token = token; this.on = handlers;           // onSpeechStart, onTurnEnd, onTranscript, onEmpty, onError
    this.gen = 0; this.epoch = 0; this.sources = []; this.cache = new Map(); this.speaking = 0; this.spoken = false;
    this.connected = false; this.capturing = false; this.closed = false;
  }

  // Call synchronously inside the click handler: browsers only allow audio after a user gesture.
  unlock() {
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.ctx.resume();
  }

  async connect() {
    const warm = await fetch("/api/voice/warmup", { method: "POST" });
    if (!warm.ok) throw new Error((await warm.json().catch(() => ({}))).detail || "The local voice is not available");
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    await this.ctx.resume();
    await this.ctx.audioWorklet.addModule("/static/pcm-worklet.js");
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    this.ws = new WebSocket(`${proto}//${location.host}/api/voice/stream?token=${encodeURIComponent(this.token)}`);
    this.ws.binaryType = "arraybuffer";
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("The voice connection timed out")), 12000);
      this.ws.onmessage = e => {
        const m = this._parse(e.data);
        if (m && m.type === "ready") { clearTimeout(timer); resolve(); }
        if (m && m.type === "error") { clearTimeout(timer); reject(new Error(m.message)); }
      };
      this.ws.onerror = () => { clearTimeout(timer); reject(new Error("The voice connection failed")); };
    });
    this.ws.onmessage = e => this._receive(e.data);
    this.ws.onclose = () => { const was = this.connected; this.connected = false; if (was && !this.closed) this.on.onError("The microphone connection dropped."); };
    this.connected = true;
    this.mic = this.ctx.createMediaStreamSource(this.stream);
    this.worklet = new AudioWorkletNode(this.ctx, "pythagoras-pcm");
    const mute = this.ctx.createGain(); mute.gain.value = 0;
    this.mic.connect(this.worklet); this.worklet.connect(mute); mute.connect(this.ctx.destination);
    this.worklet.port.onmessage = e => { if (this.capturing && this.ws.readyState === WebSocket.OPEN) this.ws.send(e.data); };
  }

  _parse(raw) { try { return JSON.parse(raw); } catch { return null; } }

  _receive(raw) {
    const m = this._parse(raw);
    if (!m) return;
    if (m.type === "error") return this.on.onError(m.message);
    if (m.epoch !== this.epoch) return;               // about a question we already left
    if (m.type === "speech_start") this.on.onSpeechStart();
    if (m.type === "turn_end") { this.capturing = false; this.on.onTurnEnd(); }
    if (m.type === "transcript") this.on.onTranscript(m.text, m.speech_s);
    if (m.type === "empty") { this.capturing = false; this.on.onEmpty(); }
  }

  listen(on) {
    clearTimeout(this.openTimer);
    const set = () => {
      this.capturing = on;
      if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ type: "listen", enabled: on, epoch: ++this.epoch }));
    };
    if (on) this.openTimer = setTimeout(set, 250);    // let the loudspeaker's tail die out first
    else set();
  }

  finish() {                                          // the student pressed "I'm done"
    if (this.capturing && this.ws.readyState === WebSocket.OPEN) { this.ws.send(JSON.stringify({ type: "finish" })); return true; }
    return false;
  }

  async _fetch(text, onChunk, signal) {
    const r = await fetch("/api/voice/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }), signal });
    if (!r.ok) throw new Error("Speech synthesis failed");
    const reader = r.body.getReader(), decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let cut;
      while ((cut = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, cut); buffer = buffer.slice(cut + 1);
        if (!line.trim()) continue;
        const chunk = JSON.parse(line);
        if (chunk.error) throw new Error(chunk.error);
        await onChunk(Uint8Array.from(atob(chunk.audio), c => c.charCodeAt(0)).buffer);
      }
    }
  }

  // Fetch lines we know we will say (acknowledgements), so they play with zero delay. Only while Pythagoras is
  // silent: the server synthesizes one sentence at a time, so a preload during a line stalls that line mid-speech.
  async preload(texts) {
    for (const text of texts) {
      while ((this.speaking || !this.spoken) && !this.closed) await new Promise(r => setTimeout(r, 150));   // after the first line
      if (this.closed) return;
      if (this.cache.has(text)) continue;
      const chunks = [];
      try { await this._fetch(text, async c => { chunks.push(c); }); this.cache.set(text, chunks); } catch { /* played uncached */ }
    }
  }

  // Resolves when the line has finished playing (or was interrupted). onStart fires at the first sound.
  async speak(text, onStart) {
    this.speaking++;
    try { return await this._speak(text, onStart); } finally { this.speaking--; this.spoken = true; }
  }

  async _speak(text, onStart) {
    this.stop();
    const gen = ++this.gen, ctx = this.ctx;
    this.abort = new AbortController();
    let next = 0, started = false;
    const schedule = async bytes => {
      const buf = await ctx.decodeAudioData(bytes.slice(0));   // decoding detaches the buffer: keep the cached one
      if (gen !== this.gen) return;
      const src = ctx.createBufferSource();
      src.buffer = buf; src.connect(ctx.destination);
      const at = Math.max(ctx.currentTime + 0.02, next);
      src.start(at); next = at + buf.duration;
      this.sources.push(src);
      if (!started) { started = true; if (onStart) onStart(); }
    };
    try {
      const cached = this.cache.get(text);
      if (cached) for (const c of cached) await schedule(c);
      else {
        const chunks = [];
        await this._fetch(text, async c => { chunks.push(c); await schedule(c); }, this.abort.signal);
        if (gen === this.gen && chunks.length) { this.cache.set(text, chunks); if (this.cache.size > 24) this.cache.delete(this.cache.keys().next().value); }
      }
    } catch (e) {
      if (gen !== this.gen) return;
      throw e;
    }
    await new Promise(resolve => {
      const wait = () => (gen !== this.gen || ctx.currentTime >= next) ? resolve() : setTimeout(wait, 40);
      wait();
    });
  }

  stop() {
    this.gen++;
    if (this.abort) this.abort.abort();
    for (const s of this.sources) { try { s.stop(); s.disconnect(); } catch { /* already ended */ } }
    this.sources = [];
  }

  close() {
    this.closed = true; this.connected = false; this.capturing = false;
    clearTimeout(this.openTimer); this.stop();
    if (this.worklet) { this.worklet.port.postMessage("stop"); this.worklet.disconnect(); }
    if (this.mic) this.mic.disconnect();
    if (this.stream) this.stream.getTracks().forEach(t => t.stop());
    if (this.ws) this.ws.close();
    if (this.ctx) this.ctx.close().catch(() => { });
  }
}
window.LocalVoice = LocalVoice;

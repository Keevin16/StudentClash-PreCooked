/* Browser microphone -> 16 kHz PCM. Stateful resampler preserves fractional offsets. */
class PythagorasPCM extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.position = 0;
    this.previous = 0;
    this.block = new Int16Array(320);
    this.filled = 0;
    this.enabled = true;
    this.port.onmessage = e => { this.enabled = e.data !== 'stop'; };
  }
  process(inputs) {
    const samples = inputs[0]?.[0];
    if (!this.enabled || !samples?.length) return true;
    // Linear interpolation with one-sample history, including non-integral 44.1 kHz ratios.
    while (this.position < samples.length - 1) {
      const index = Math.floor(this.position);
      const a = index < 0 ? this.previous : samples[index];
      const b = samples[index + 1];
      const value = a + (b - a) * (this.position - index);
      this.block[this.filled++] = Math.round(Math.max(-1, Math.min(1, value)) * 32767);
      if (this.filled === this.block.length) {
        this.port.postMessage(this.block.buffer, [this.block.buffer]);
        this.block = new Int16Array(320); this.filled = 0;
      }
      this.position += this.ratio;
    }
    this.position -= samples.length;
    this.previous = samples[samples.length - 1];
    return true;
  }
}
registerProcessor('pythagoras-pcm', PythagorasPCM);

import { AudioFrame } from '@livekit/rtc-node';
import { once } from 'node:events';
import { afterEach, expect, it } from 'vitest';
import { WebSocketServer } from 'ws';
import { STT } from './stt.js';

let server: WebSocketServer;

afterEach(async () => {
  for (const socket of server?.clients ?? []) socket.terminate();
  if (server) await new Promise<void>((resolve) => server.close(() => resolve()));
});

function frame(amplitude: number) {
  const data = new Int16Array(1600);
  for (let i = 0; i < data.length; i++) data[i] = Math.round(amplitude * Math.sin(i / 4));
  return new AudioFrame(data, 16000, 1, 1600);
}

it('forwards trailing silence to Deepgram', async () => {
  server = new WebSocketServer({ host: '127.0.0.1', port: 0 });
  await once(server, 'listening');
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('expected TCP server');
  let audioBytes = 0;
  let closeStream!: () => void;
  const closed = new Promise<void>((resolve) => (closeStream = resolve));
  const connected = new Promise<void>((resolve) => {
    server.on('connection', (socket) => {
      resolve();
      socket.on('message', (data, isBinary) => {
        if (isBinary) audioBytes += (data as Buffer).length;
        else if (String(data).includes('CloseStream')) closeStream();
      });
    });
  });
  const provider = new STT({ apiKey: 'test', baseUrl: `ws://127.0.0.1:${address.port}` });
  const stream = provider.stream();
  const drained = (async () => {
    for await (const _ of stream) {
    }
  })();
  await connected;
  for (let i = 0; i < 10; i++) stream.pushFrame(frame(8000));
  for (let i = 0; i < 30; i++) stream.pushFrame(frame(0));
  stream.endInput();
  await closed;
  stream.close();
  await drained;
  const speechBytes = 10 * 1600 * 2;
  const silenceBytes = 30 * 1600 * 2;
  const silenceSentMs = ((audioBytes - speechBytes) / 2 / 16000) * 1000;
  console.log(
    `pushed 1000 ms speech + 3000 ms silence -> socket got ${audioBytes} audio bytes, ` +
      `${silenceSentMs.toFixed(0)} ms of the silence`,
  );
  expect(audioBytes).toBe(speechBytes + silenceBytes);
});

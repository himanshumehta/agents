import { AudioFrame, ByteStreamWriter, Room, RoomEvent } from '@livekit/rtc-node';
import { ReadableStream } from 'node:stream/web';
import { beforeEach, expect, it, vi } from 'vitest';
import { initializeLogger } from '../../log.js';
import { SynthesizeStream, TTS } from '../../tts/tts.js';
import { Agent } from '../agent.js';
import { AgentSession } from '../agent_session.js';
import { AudioOutput } from '../io.js';
import { DataStreamAudioOutput } from './datastream_io.js';

initializeLogger({ pretty: false, level: 'error' });

function fakeRoom() {
  const avatar = { identity: 'avatar' };
  const remoteParticipants = new Map<string, unknown>([[avatar.identity, avatar]]);
  const sent = { bytes: 0 };
  const room = new Room();
  Object.defineProperties(room, {
    isConnected: { value: true },
    localParticipant: {
      value: {
        performRpc: vi.fn(async () => ''),
        registerRpcMethod: vi.fn(),
        streamBytes: vi.fn(
          async () =>
            new ByteStreamWriter(
              new WritableStream<Uint8Array>({
                write(chunk) {
                  sent.bytes += chunk.byteLength;
                },
              }),
              {
                streamId: 's',
                mimeType: 'application/octet-stream',
                topic: 'lk.audio_stream',
                timestamp: 0,
                name: 'audio',
              },
            ),
        ),
      },
    },
    remoteParticipants: { value: remoteParticipants },
  });
  const avatarLeaves = () => {
    remoteParticipants.delete(avatar.identity);
    room.emit(RoomEvent.ParticipantDisconnected, avatar as never);
  };
  return { room, sent, avatarLeaves };
}

class VoiceOnlyOutput extends AudioOutput {
  frames = 0;
  constructor() {
    super(24000);
  }
  override async captureFrame(f: AudioFrame): Promise<void> {
    await super.captureFrame(f);
    this.frames++;
    this.onPlaybackStarted(Date.now());
  }
  override flush(): void {
    super.flush();
    if (this.pendingPlayoutSegments) {
      this.onPlaybackFinished({ playbackPosition: 0.2, interrupted: false });
    }
  }
  override clearBuffer(): void {
    if (this.pendingPlayoutSegments) {
      this.onPlaybackFinished({ playbackPosition: 0, interrupted: true });
    }
  }
}

class StubTTS extends TTS {
  label = 'stub';
  constructor() {
    super(24000, 1, { streaming: true });
  }
  synthesize(): never {
    throw new Error('unused');
  }
  stream(): SynthesizeStream {
    throw new Error('unused');
  }
}

class FrameAgent extends Agent {
  constructor() {
    super({ instructions: 'test' });
  }
  override async ttsNode(): Promise<ReadableStream<AudioFrame> | null> {
    return new ReadableStream<AudioFrame>({
      start(c) {
        for (let i = 0; i < 10; i++) c.enqueue(new AudioFrame(new Int16Array(480), 24000, 1, 480));
        c.close();
      },
    });
  }
}

const settle = () => new Promise((r) => setTimeout(r, 2000));

beforeEach(() => {
  DataStreamAudioOutput._playbackFinishedRpcRegistered = false;
  DataStreamAudioOutput._playbackFinishedHandlers = {};
});

async function run(avatarLeavesMidReply: boolean) {
  const { room, sent, avatarLeaves } = fakeRoom();
  const session = new AgentSession({ tts: new StubTTS() });
  const avatarOutput = new DataStreamAudioOutput({
    room,
    destinationIdentity: 'avatar',
    sampleRate: 24000,
  });
  session.output.audio = avatarOutput;
  await session.start({ agent: new FrameAgent() });
  const first = session.say('Here is the first reply.');
  await vi.waitFor(() => expect(sent.bytes).toBe(10 * 480 * 2));
  if (!avatarLeavesMidReply) {
    avatarOutput.onPlaybackFinished({ playbackPosition: 0.2, interrupted: false });
    await first.waitForPlayout();
  }
  avatarLeaves();
  const voice = new VoiceOnlyOutput();
  session.output.audio = voice;
  const fallback = session.say('My video dropped, but I am still here in voice.');
  await settle();
  console.log(
    `avatar left ${avatarLeavesMidReply ? 'mid-reply' : 'between replies'} -> new output got ${voice.frames} frames; ` +
      `first reply done=${first.done()}, fallback done=${fallback.done()}, agentState=${session.agentState}`,
  );
  await session.close();
  return voice.frames;
}

it('swap after the avatar leaves between replies', async () => {
  expect(await run(false)).toBe(10);
});

it('swap after the avatar leaves mid-reply', async () => {
  expect(await run(true)).toBe(10);
});

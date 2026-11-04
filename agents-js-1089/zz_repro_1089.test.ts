import {
  AudioFrame,
  LocalAudioTrack,
  TrackPublishOptions,
  TrackSource,
} from "@livekit/rtc-node";
import { ReadableStream } from "node:stream/web";
import { afterEach, expect, it, vi } from "vitest";
import { initializeLogger } from "../log.js";
import { Agent } from "./agent.js";
import { AgentSession } from "./agent_session.js";
import { ParticipantAudioOutput } from "./room_io/_output.js";

function frame(): AudioFrame {
  const samples = 480;
  return new AudioFrame(new Int16Array(samples), 24000, 1, samples);
}

class GreetingAgent extends Agent {
  constructor(private readonly allowInterruptions: boolean) {
    super({ instructions: "test" });
  }

  async onEnter(): Promise<void> {
    const audio = new ReadableStream<AudioFrame>({
      start(controller) {
        for (let i = 0; i < 10; i++) controller.enqueue(frame());
        controller.close();
      },
    });
    this.session.say("Hello, how can I help you today?", {
      audio,
      allowInterruptions: this.allowInterruptions,
    });
  }
}

function neverSubscribedOutput(): ParticipantAudioOutput {
  const room = {
    localParticipant: {
      publishTrack: async () => ({
        sid: "TR_never_subscribed",
        waitForSubscription: () => new Promise<void>(() => {}),
      }),
    },
  };
  const output = new ParticipantAudioOutput(room as never, {
    sampleRate: 24000,
    numChannels: 1,
    trackPublishOptions: new TrackPublishOptions({
      source: TrackSource.SOURCE_MICROPHONE,
    }),
  });
  void output.start(new AbortController().signal);
  return output;
}

afterEach(() => {
  vi.restoreAllMocks();
});

it.each([{ allowInterruptions: false }, { allowInterruptions: true }])(
  "session.close() returns when the participant left before subscribing (allowInterruptions: $allowInterruptions)",
  async ({ allowInterruptions }) => {
    initializeLogger({ pretty: false, level: "silent" });
    vi.spyOn(LocalAudioTrack, "createAudioTrack").mockReturnValue(
      {} as LocalAudioTrack,
    );
    const session = new AgentSession({});
    session.output.audio = neverSubscribedOutput();
    await session.start({ agent: new GreetingAgent(allowInterruptions) });
    await new Promise((resolve) => setTimeout(resolve, 200));

    const startedAt = Date.now();
    const result = await Promise.race([
      session.close().then(() => "closed"),
      new Promise<string>((resolve) =>
        setTimeout(() => resolve("still closing"), 3000),
      ),
    ]);
    console.log(
      `session.close(): ${result} after ${Date.now() - startedAt} ms`,
    );
    expect(result).toBe("closed");
  },
  10_000,
);

it("session.shutdown({ drain: true }) closes when the participant left before subscribing", async () => {
  initializeLogger({ pretty: false, level: "silent" });
  vi.spyOn(LocalAudioTrack, "createAudioTrack").mockReturnValue(
    {} as LocalAudioTrack,
  );
  const session = new AgentSession({});
  session.output.audio = neverSubscribedOutput();
  await session.start({ agent: new GreetingAgent(true) });
  await new Promise((resolve) => setTimeout(resolve, 200));

  const startedAt = Date.now();
  const closed = new Promise<string>((resolve) =>
    session.once("close", () => resolve("closed")),
  );
  session.shutdown({ drain: true });
  const result = await Promise.race([
    closed,
    new Promise<string>((resolve) =>
      setTimeout(() => resolve("still closing"), 5000),
    ),
  ]);
  console.log(
    `session.shutdown({ drain: true }): ${result} after ${Date.now() - startedAt} ms`,
  );
  expect(result).toBe("closed");
}, 10_000);

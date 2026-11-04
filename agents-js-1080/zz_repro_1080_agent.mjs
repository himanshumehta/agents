import { defineAgent } from './agents/dist/index.js';

const say = (line) => process.stdout.write(`ZZ ${line}\n`);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const METHOD = 'lk_end_of_utterance_multilingual';

export default defineAgent({
  entry: async (ctx) => {
    const mode = process.env.ZZ_MODE;
    say(`entry started, mode=${mode}, process.connected=${process.connected}`);
    if (mode === 'await') {
      process.connected = false;
      say('process.connected forced to false, awaiting doInference with no try/catch');
      try {
        await ctx.inferenceExecutor.doInference(METHOD, []);
      } finally {
        process.connected = true;
      }
    } else if (mode === 'floating') {
      process.connected = false;
      say('process.connected forced to false, calling doInference with no await and no catch');
      ctx.inferenceExecutor.doInference(METHOD, []);
      await sleep(300);
      process.connected = true;
      say('entry still running 300 ms after the rejection, calling ctx.shutdown()');
      ctx.shutdown('repro done');
    } else if (mode === 'disconnect') {
      for (let i = 1; ; i++) {
        const out = await ctx.inferenceExecutor.doInference(METHOD, []);
        if (i <= 3) say(`inference ${i} answered: ${JSON.stringify(out)}`);
        if (i === 3) say('ready for the parent to close the channel');
        await sleep(50);
      }
    }
  },
});

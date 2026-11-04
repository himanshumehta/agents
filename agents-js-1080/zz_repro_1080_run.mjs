import { fork } from 'node:child_process';
import { createInterface } from 'node:readline';

const mode = process.argv[2];
const main = new URL('./agents/dist/ipc/job_proc_lazy_main.js', import.meta.url).pathname;
const agent = new URL('./zz_repro_1080_agent.mjs', import.meta.url).pathname;
const child = fork(main, [agent], {
  stdio: ['ignore', 'pipe', 'pipe', 'ipc'],
  env: { ...process.env, ZZ_MODE: mode },
});
const interesting = /inference|IPC|Unhandled|crash|shutting down|orphan|closed the IPC|entrypoint|exiting|error/i;
let stderr = '';
createInterface({ input: child.stdout }).on('line', (line) => {
  if (line.startsWith('ZZ ')) {
    console.log(`  agent | ${line.slice(3)}`);
    if (mode === 'disconnect' && line.includes('ready for the parent')) {
      child.disconnect();
      console.log('  parent| child.disconnect(): IPC channel closed');
    }
    return;
  }
  let rec;
  try {
    rec = JSON.parse(line);
  } catch {
    console.log(`  stdout| ${line}`);
    return;
  }
  const level = { 10: 'trace', 20: 'debug', 30: 'info', 40: 'warn', 50: 'error', 60: 'fatal' }[rec.level] ?? rec.level;
  const err = rec.error?.message ?? rec.err?.message ?? rec.error ?? rec.err;
  if (interesting.test(rec.msg ?? '') || err) {
    console.log(`  job   | ${level} "${rec.msg}"${err ? ` error="${typeof err === 'string' ? err : JSON.stringify(err)}"` : ''}`);
  }
});
child.stderr.on('data', (d) => (stderr += d));
child.on('message', (msg) => {
  if (msg.case === 'initializeResponse') {
    child.send({
      case: 'startJobRequest',
      value: {
        runningJob: {
          acceptArguments: { name: '', identity: '', metadata: '' },
          job: { id: 'AJ_repro1080', room: { sid: 'RM_repro1080', name: 'repro1080' }, agentName: '' },
          url: '',
          token: '',
          workerId: 'W_repro1080',
          fakeJob: true,
        },
      },
    });
  } else if (msg.case === 'inferenceRequest') {
    child.send({ case: 'inferenceResponse', value: { requestId: msg.value.requestId, data: { eouProbability: 0.9 } } });
  }
});
child.send({ case: 'initializeRequest', value: { loggerOptions: { pretty: false, level: 'debug' }, sessionEndTimeout: 2000 } });
child.on('exit', (code, signal) => {
  for (const l of stderr.split('\n').filter(Boolean)) console.log(`  stderr| ${l}`);
  const uncaught = /Uncaught|uncaughtException|^\s+at /m.test(stderr);
  console.log(`  => job process exit code=${code} signal=${signal}; uncaught exception on stderr: ${uncaught ? 'YES' : 'no'}`);
});

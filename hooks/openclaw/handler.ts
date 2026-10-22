import type { HookHandler } from 'openclaw/hooks';

const REMINDER_NAME = 'SHARED_CONTEXT_HANDOFF_REMINDER.md';
const REMINDER_PATH = REMINDER_NAME;
const REMINDER_CONTENT = `# Shared Context Handoff

- For staged tasks, read Shared Context before work and every transition.
- Use only structured Goal, Constraints, Verifiers handoffs.
- TRIAGE/PLAN: no implementation. EXECUTE: respect scope.
- VALIDATE: run declared tests; reject any failure.
- MONITOR: demand observed evidence before AUTOMATE.`;

type BootstrapFile = { path?: string; name?: string; virtual?: boolean; [key: string]: unknown };
const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;
const isInjectedReminderFile = (value: unknown): value is BootstrapFile =>
  isObject(value) && value.path === REMINDER_PATH && value.name === REMINDER_NAME && value.virtual === true;

const handler: HookHandler = async (event) => {
  if (!event || event.type !== 'agent' || event.action !== 'bootstrap') return;
  if (!event.context || typeof event.context !== 'object') return;
  const sessionKey = event.sessionKey || '';
  if (sessionKey.includes(':subagent:')) return;
  if (!Array.isArray(event.context.bootstrapFiles)) return;

  const occupiedByOtherFile = event.context.bootstrapFiles.some(
    (file) => isObject(file) && file.path === REMINDER_PATH && !isInjectedReminderFile(file),
  );
  if (occupiedByOtherFile) return;

  const cleaned = event.context.bootstrapFiles.filter(
    (file, index, files) =>
      !isInjectedReminderFile(file) ||
      files.findIndex((candidate) => isInjectedReminderFile(candidate)) === index,
  );
  const reminderFile = {
    name: REMINDER_NAME,
    path: REMINDER_PATH,
    content: REMINDER_CONTENT,
    missing: false,
    virtual: true,
  };
  const existingIndex = cleaned.findIndex((file) => isInjectedReminderFile(file));
  if (existingIndex === -1) cleaned.push(reminderFile);
  else cleaned[existingIndex] = reminderFile;
  event.context.bootstrapFiles = cleaned;
};

export default handler;

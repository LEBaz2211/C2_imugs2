import type { AssistantMessageResponse } from "./api";

export const LEGACY_ASSISTANT_SESSION_STORAGE_KEY = "c2_imugs2_assistant_session_v1";
export const ASSISTANT_HISTORY_STORAGE_KEY = "c2_imugs2_assistant_conversations_v2";
export const MAX_ASSISTANT_TRANSCRIPT_ITEMS = 80;
export const MAX_ASSISTANT_CONVERSATIONS = 20;

export type AssistantTranscriptItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: AssistantMessageResponse;
  debugRequested?: boolean;
};

export type AssistantConversationRecord = {
  conversationId: string;
  messages: AssistantTranscriptItem[];
  createdAt: string;
  updatedAt: string;
};

export type AssistantConversationStore = {
  activeConversationId: string;
  conversations: AssistantConversationRecord[];
};

export type AssistantConversationSummary = {
  conversationId: string;
  title: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
  active: boolean;
};

export type AssistantHistoryWriteResult = {
  store: AssistantConversationStore;
  persisted: boolean;
  debugTracesStripped: boolean;
  evictedConversationIds: string[];
};

export type AssistantHistoryStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

type StoredAssistantConversation = {
  conversation_id?: unknown;
  messages?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
};

type StoredAssistantConversationStore = {
  version?: unknown;
  active_conversation_id?: unknown;
  conversations?: unknown;
};

export function createAssistantConversation({
  conversationId = createConversationId(),
  now = currentTimestamp(),
}: {
  conversationId?: string;
  now?: string;
} = {}): AssistantConversationRecord {
  const timestamp = normalizeTimestamp(now, currentTimestamp());
  return {
    conversationId: normalizeConversationId(conversationId) ?? createConversationId(),
    messages: [],
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

export function createAssistantConversationStore(
  conversation = createAssistantConversation(),
): AssistantConversationStore {
  const normalized = normalizeConversation(conversation);
  return {
    activeConversationId: normalized.conversationId,
    conversations: [normalized],
  };
}

export function readAssistantConversationStore(
  storage: AssistantHistoryStorage | undefined = browserStorage(),
): AssistantConversationStore {
  if (!storage) return createAssistantConversationStore();

  const stored = readJson(storage, ASSISTANT_HISTORY_STORAGE_KEY);
  if (isStoredConversationStore(stored)) {
    return normalizeAssistantConversationStore(storedConversationStore(stored));
  }

  const legacy = readJson(storage, LEGACY_ASSISTANT_SESSION_STORAGE_KEY);
  const migrated = migrateLegacyAssistantSession(legacy);
  if (!migrated) return createAssistantConversationStore();

  const result = writeAssistantConversationStore(migrated, storage);
  return result.persisted ? result.store : migrated;
}

export function writeAssistantConversationStore(
  store: AssistantConversationStore,
  storage: AssistantHistoryStorage | undefined = browserStorage(),
): AssistantHistoryWriteResult {
  const normalized = normalizeAssistantConversationStore(store);
  if (!storage) return writeFailure(normalized);

  if (persistStore(storage, normalized)) {
    removeLegacyStore(storage);
    return writeSuccess(normalized);
  }

  const withoutDebug = stripAssistantDebugTraces(normalized);
  if (persistStore(storage, withoutDebug)) {
    removeLegacyStore(storage);
    return writeSuccess(withoutDebug, true);
  }

  let candidate = withoutDebug;
  const evictedConversationIds: string[] = [];
  for (const conversation of oldestInactiveConversations(candidate)) {
    evictedConversationIds.push(conversation.conversationId);
    candidate = deleteAssistantConversation(candidate, conversation.conversationId);
    if (persistStore(storage, candidate)) {
      removeLegacyStore(storage);
      return writeSuccess(candidate, true, evictedConversationIds);
    }
  }

  return writeFailure(normalized);
}

export function normalizeAssistantConversationStore(
  store: AssistantConversationStore,
): AssistantConversationStore {
  const fallbackTimestamp = currentTimestamp();
  const byId = new Map<string, AssistantConversationRecord>();

  for (const value of Array.isArray(store.conversations) ? store.conversations : []) {
    const conversation = normalizeConversation(value, fallbackTimestamp);
    const existing = byId.get(conversation.conversationId);
    if (!existing || compareConversationRecency(conversation, existing) < 0) {
      byId.set(conversation.conversationId, conversation);
    }
  }

  if (byId.size === 0) return createAssistantConversationStore();

  const requestedActiveId = normalizeConversationId(store.activeConversationId);
  const ordered = [...byId.values()].sort(compareConversationRecency);
  const activeConversationId = requestedActiveId && byId.has(requestedActiveId)
    ? requestedActiveId
    : ordered[0].conversationId;
  const retained = retainBoundedConversations(ordered, activeConversationId);

  return {
    activeConversationId,
    conversations: retained,
  };
}

export function getActiveAssistantConversation(
  store: AssistantConversationStore,
): AssistantConversationRecord {
  const normalized = normalizeAssistantConversationStore(store);
  return normalized.conversations.find(
    (conversation) => conversation.conversationId === normalized.activeConversationId,
  ) ?? normalized.conversations[0];
}

export function assistantTranscriptItems(
  store: AssistantConversationStore,
): AssistantTranscriptItem[] {
  return normalizeAssistantConversationStore(store).conversations.flatMap(
    (conversation) => conversation.messages,
  );
}

export function updateAssistantConversation(
  store: AssistantConversationStore,
  conversationId: string,
  update: (
    conversation: AssistantConversationRecord,
  ) => AssistantConversationRecord,
): AssistantConversationStore {
  const normalized = normalizeAssistantConversationStore(store);
  const targetId = normalizeConversationId(conversationId);
  if (!targetId || !normalized.conversations.some((item) => item.conversationId === targetId)) {
    return normalized;
  }

  const conversations = normalized.conversations.map((conversation) => {
    if (conversation.conversationId !== targetId) return conversation;
    const updated = update(conversation);
    return normalizeConversation({
      ...updated,
      conversationId: targetId,
      createdAt: conversation.createdAt,
    });
  });
  return normalizeAssistantConversationStore({ ...normalized, conversations });
}

export function updateAssistantConversationMessages(
  store: AssistantConversationStore,
  conversationId: string,
  update: AssistantTranscriptItem[] | ((messages: AssistantTranscriptItem[]) => AssistantTranscriptItem[]),
  now = currentTimestamp(),
): AssistantConversationStore {
  return updateAssistantConversation(store, conversationId, (conversation) => ({
    ...conversation,
    messages: typeof update === "function" ? update(conversation.messages) : update,
    updatedAt: normalizeTimestamp(now, currentTimestamp()),
  }));
}

export function selectAssistantConversation(
  store: AssistantConversationStore,
  conversationId: string,
): AssistantConversationStore {
  const normalized = normalizeAssistantConversationStore(store);
  const targetId = normalizeConversationId(conversationId);
  if (!targetId || !normalized.conversations.some((item) => item.conversationId === targetId)) {
    return normalized;
  }
  return { ...normalized, activeConversationId: targetId };
}

export function addAssistantConversation(
  store: AssistantConversationStore,
  conversation = createAssistantConversation(),
): AssistantConversationStore {
  const normalized = normalizeAssistantConversationStore(store);
  const added = normalizeConversation(conversation);
  return normalizeAssistantConversationStore({
    activeConversationId: added.conversationId,
    conversations: [added, ...normalized.conversations.filter(
      (item) => item.conversationId !== added.conversationId,
    )],
  });
}

export function startNewAssistantConversation(
  store: AssistantConversationStore,
  conversation = createAssistantConversation(),
): AssistantConversationStore {
  const normalized = normalizeAssistantConversationStore(store);
  if (getActiveAssistantConversation(normalized).messages.length === 0) return normalized;
  return addAssistantConversation(normalized, conversation);
}

export function deleteAssistantConversation(
  store: AssistantConversationStore,
  conversationId: string,
  replacement = createAssistantConversation(),
): AssistantConversationStore {
  const normalized = normalizeAssistantConversationStore(store);
  const targetId = normalizeConversationId(conversationId);
  if (!targetId || !normalized.conversations.some((item) => item.conversationId === targetId)) {
    return normalized;
  }

  const remaining = normalized.conversations.filter(
    (conversation) => conversation.conversationId !== targetId,
  );
  if (remaining.length === 0) return createAssistantConversationStore(replacement);

  const activeConversationId = normalized.activeConversationId === targetId
    ? [...remaining].sort(compareConversationRecency)[0].conversationId
    : normalized.activeConversationId;
  return normalizeAssistantConversationStore({ activeConversationId, conversations: remaining });
}

export function assistantConversationTitle(
  conversation: AssistantConversationRecord,
  maxLength = 48,
): string {
  const firstUserMessage = conversation.messages.find((message) => message.role === "user")?.text.trim();
  if (!firstUserMessage) return "New conversation";
  if (maxLength < 2 || firstUserMessage.length <= maxLength) return firstUserMessage;
  return `${firstUserMessage.slice(0, maxLength - 1).trimEnd()}…`;
}

export function assistantConversationSummaries(
  store: AssistantConversationStore,
): AssistantConversationSummary[] {
  const normalized = normalizeAssistantConversationStore(store);
  return [...normalized.conversations].sort(compareConversationRecency).map((conversation) => ({
    conversationId: conversation.conversationId,
    title: assistantConversationTitle(conversation),
    messageCount: conversation.messages.length,
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
    active: conversation.conversationId === normalized.activeConversationId,
  }));
}

function migrateLegacyAssistantSession(value: unknown): AssistantConversationStore | undefined {
  if (!isRecord(value)) return undefined;
  const conversationId = normalizeConversationId(value.conversation_id);
  if (!conversationId || !Array.isArray(value.messages)) return undefined;

  const messages = normalizeTranscript(value.messages);
  const timestamp = legacyTimestamp(messages) ?? currentTimestamp();
  return createAssistantConversationStore({
    conversationId,
    messages,
    createdAt: timestamp,
    updatedAt: timestamp,
  });
}

function storedConversationStore(value: StoredAssistantConversationStore): AssistantConversationStore {
  const conversations = (value.conversations as StoredAssistantConversation[]).flatMap((item) => {
    if (!isRecord(item)) return [];
    const conversationId = normalizeConversationId(item.conversation_id);
    if (!conversationId || !Array.isArray(item.messages)) return [];
    return [{
      conversationId,
      messages: normalizeTranscript(item.messages),
      createdAt: typeof item.created_at === "string" ? item.created_at : "",
      updatedAt: typeof item.updated_at === "string" ? item.updated_at : "",
    }];
  });
  return {
    activeConversationId: typeof value.active_conversation_id === "string"
      ? value.active_conversation_id
      : "",
    conversations,
  };
}

function normalizeConversation(
  value: AssistantConversationRecord,
  fallbackTimestamp = currentTimestamp(),
): AssistantConversationRecord {
  const createdAt = normalizeTimestamp(value.createdAt, fallbackTimestamp);
  return {
    conversationId: normalizeConversationId(value.conversationId) ?? createConversationId(),
    messages: normalizeTranscript(value.messages),
    createdAt,
    updatedAt: normalizeTimestamp(value.updatedAt, createdAt),
  };
}

function normalizeTranscript(value: unknown): AssistantTranscriptItem[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    if (typeof item.id !== "string" || !item.id.trim()) return [];
    if (item.role !== "user" && item.role !== "assistant") return [];
    if (typeof item.text !== "string") return [];
    const role: AssistantTranscriptItem["role"] = item.role;
    const response = isRecord(item.response)
      ? item.response as AssistantMessageResponse
      : undefined;
    return [{
      id: item.id,
      role,
      text: item.text,
      ...(response ? { response } : {}),
      ...(typeof item.debugRequested === "boolean" ? { debugRequested: item.debugRequested } : {}),
    } satisfies AssistantTranscriptItem];
  }).slice(-MAX_ASSISTANT_TRANSCRIPT_ITEMS);
}

function stripAssistantDebugTraces(
  store: AssistantConversationStore,
): AssistantConversationStore {
  return {
    ...store,
    conversations: store.conversations.map((conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) => {
        if (!message.response || message.response.debug_trace === undefined) return message;
        const { debug_trace: _debugTrace, ...response } = message.response;
        return { ...message, response: response as AssistantMessageResponse };
      }),
    })),
  };
}

function retainBoundedConversations(
  conversations: AssistantConversationRecord[],
  activeConversationId: string,
): AssistantConversationRecord[] {
  if (conversations.length <= MAX_ASSISTANT_CONVERSATIONS) return conversations;
  const active = conversations.find((item) => item.conversationId === activeConversationId);
  const retained = conversations
    .filter((item) => item.conversationId !== activeConversationId)
    .slice(0, active ? MAX_ASSISTANT_CONVERSATIONS - 1 : MAX_ASSISTANT_CONVERSATIONS);
  return active ? [active, ...retained].sort(compareConversationRecency) : retained;
}

function oldestInactiveConversations(
  store: AssistantConversationStore,
): AssistantConversationRecord[] {
  return store.conversations
    .filter((conversation) => conversation.conversationId !== store.activeConversationId)
    .sort((left, right) => compareConversationRecency(right, left));
}

function compareConversationRecency(
  left: AssistantConversationRecord,
  right: AssistantConversationRecord,
): number {
  const byUpdatedAt = right.updatedAt.localeCompare(left.updatedAt);
  if (byUpdatedAt !== 0) return byUpdatedAt;
  const byCreatedAt = right.createdAt.localeCompare(left.createdAt);
  if (byCreatedAt !== 0) return byCreatedAt;
  return left.conversationId.localeCompare(right.conversationId);
}

function legacyTimestamp(messages: AssistantTranscriptItem[]): string | undefined {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const observedAt = messages[index].response?.picture_observed_at;
    if (typeof observedAt === "string" && validTimestamp(observedAt)) {
      return new Date(observedAt).toISOString();
    }
  }
  return undefined;
}

function persistStore(storage: AssistantHistoryStorage, store: AssistantConversationStore): boolean {
  try {
    storage.setItem(ASSISTANT_HISTORY_STORAGE_KEY, JSON.stringify({
      version: 2,
      active_conversation_id: store.activeConversationId,
      conversations: store.conversations.map((conversation) => ({
        conversation_id: conversation.conversationId,
        messages: conversation.messages,
        created_at: conversation.createdAt,
        updated_at: conversation.updatedAt,
      })),
    }));
    return true;
  } catch {
    return false;
  }
}

function removeLegacyStore(storage: AssistantHistoryStorage) {
  try {
    storage.removeItem(LEGACY_ASSISTANT_SESSION_STORAGE_KEY);
  } catch {
    // A completed v2 write is enough; stale v1 data is ignored on later reads.
  }
}

function readJson(storage: AssistantHistoryStorage, key: string): unknown {
  try {
    return JSON.parse(storage.getItem(key) ?? "null") as unknown;
  } catch {
    return undefined;
  }
}

function isStoredConversationStore(value: unknown): value is StoredAssistantConversationStore {
  return isRecord(value)
    && value.version === 2
    && typeof value.active_conversation_id === "string"
    && Array.isArray(value.conversations);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeConversationId(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized && normalized.length <= 256 ? normalized : undefined;
}

function normalizeTimestamp(value: unknown, fallback: string): string {
  if (typeof value !== "string" || !validTimestamp(value)) return fallback;
  return new Date(value).toISOString();
}

function validTimestamp(value: string): boolean {
  return Number.isFinite(Date.parse(value));
}

function createConversationId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") return globalThis.crypto.randomUUID();
  return `conversation-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function currentTimestamp(): string {
  return new Date().toISOString();
}

function browserStorage(): AssistantHistoryStorage | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

function writeSuccess(
  store: AssistantConversationStore,
  debugTracesStripped = false,
  evictedConversationIds: string[] = [],
): AssistantHistoryWriteResult {
  return {
    store,
    persisted: true,
    debugTracesStripped,
    evictedConversationIds,
  };
}

function writeFailure(store: AssistantConversationStore): AssistantHistoryWriteResult {
  return {
    store,
    persisted: false,
    debugTracesStripped: false,
    evictedConversationIds: [],
  };
}

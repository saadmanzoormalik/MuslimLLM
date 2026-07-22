import type { ChatStreamEvent } from "./types";

export class ChatStreamParser {
  private buffer = "";
  private decoder = new TextDecoder();
  private lastSequence = new Map<string, number>();

  push(chunk: Uint8Array | string): ChatStreamEvent[] {
    this.buffer += typeof chunk === "string" ? chunk : this.decoder.decode(chunk, { stream: true });
    const frames = this.buffer.split("\n\n");
    this.buffer = frames.pop() || "";
    const events: ChatStreamEvent[] = [];
    for (const frame of frames) {
      const eventName = frame.match(/^event:\s*(.+)$/m)?.[1]?.trim();
      const dataLines = frame.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart());
      if (!eventName || !dataLines.length) continue;
      let data: ChatStreamEvent;
      try { data = JSON.parse(dataLines.join("\n")) as ChatStreamEvent; } catch { continue; }
      if (!data.type) data.type = eventName as ChatEventType;
      const previous = this.lastSequence.get(data.request_id) || 0;
      if (Number.isFinite(data.sequence) && data.sequence <= previous) continue;
      if (Number.isFinite(data.sequence)) this.lastSequence.set(data.request_id, data.sequence);
      events.push(data);
    }
    return events;
  }
}

type ChatEventType = ChatStreamEvent["type"];


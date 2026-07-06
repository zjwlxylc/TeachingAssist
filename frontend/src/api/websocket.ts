type MessageHandler = (event: MessageEvent) => void;

export class TeachingAssistSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private closedByClient = false;

  constructor(
    private readonly url: string,
    private readonly onMessage: MessageHandler,
    private readonly reconnectDelay = 3000,
    private readonly onOpen?: () => void
  ) {}

  connect() {
    this.closedByClient = false;
    this.socket = new WebSocket(this.url);
    this.socket.onopen = this.onOpen ?? null;
    this.socket.onmessage = this.onMessage;
    this.socket.onclose = () => this.scheduleReconnect();
  }

  send(payload: unknown) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  close() {
    this.closedByClient = true;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
    }
    this.socket?.close();
  }

  private scheduleReconnect() {
    if (this.closedByClient) {
      return;
    }
    this.reconnectTimer = window.setTimeout(() => this.connect(), this.reconnectDelay);
  }
}

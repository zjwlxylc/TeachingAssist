type MessageHandler = (event: MessageEvent) => void;

export class TeachingAssistSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;

  constructor(
    private readonly url: string,
    private readonly onMessage: MessageHandler,
    private readonly reconnectDelay = 3000
  ) {}

  connect() {
    this.socket = new WebSocket(this.url);
    this.socket.onmessage = this.onMessage;
    this.socket.onclose = () => this.scheduleReconnect();
  }

  send(payload: unknown) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  close() {
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
    }
    this.socket?.close();
  }

  private scheduleReconnect() {
    this.reconnectTimer = window.setTimeout(() => this.connect(), this.reconnectDelay);
  }
}

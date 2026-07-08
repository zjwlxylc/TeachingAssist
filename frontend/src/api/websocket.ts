type MessageHandler = (event: MessageEvent) => void;

export class TeachingAssistSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private closedByClient = false;
  private reconnectAttempts = 0;

  constructor(
    private readonly url: string,
    private readonly onMessage: MessageHandler,
    private readonly reconnectDelay = 3000,
    private readonly onOpen?: () => void,
    private readonly maxReconnectAttempts = 10,
    private readonly maxReconnectDelay = 30000,
    private readonly onReconnectFailed?: () => void
  ) {}

  connect() {
    // 去重：已存在连接（OPEN/CONNECTING）时不重复建连，避免组件重复渲染导致多 socket
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.closedByClient = false;
    this.socket = new WebSocket(this.url);
    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      if (this.onOpen) this.onOpen();
    };
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
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  private scheduleReconnect() {
    if (this.closedByClient) {
      return;
    }
    // 超过最大重试次数后放弃，避免无限重连打服务端
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (this.onReconnectFailed) this.onReconnectFailed();
      return;
    }
    this.reconnectAttempts += 1;
    // 指数退避并封顶
    const delay = Math.min(this.reconnectDelay * 2 ** (this.reconnectAttempts - 1), this.maxReconnectDelay);
    this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
  }
}

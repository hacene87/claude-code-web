/**
 * WebSocket Service
 * =================
 *
 * Real-time event streaming.
 */

import { io, Socket } from 'socket.io-client';
import api from './api';
import { WebSocketEvent } from '../types/api.types';

type EventHandler = (event: WebSocketEvent) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private globalHandlers: Set<EventHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  async connect(): Promise<void> {
    const serverUrl = await api.getServerURL();
    const token = await api.getAccessToken();

    if (!serverUrl || !token) {
      throw new Error('Server URL or token not available');
    }

    // Create WebSocket connection
    const wsUrl = serverUrl.replace(/^http/, 'ws');

    this.socket = io(wsUrl, {
      auth: { token },
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    this.setupListeners();
  }

  private setupListeners(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Handle all events
    this.socket.onAny((eventType: string, data: any) => {
      const event: WebSocketEvent = {
        type: eventType,
        timestamp: new Date().toISOString(),
        payload: data,
      };

      // Notify specific handlers
      const handlers = this.handlers.get(eventType);
      if (handlers) {
        handlers.forEach((handler) => handler(event));
      }

      // Notify global handlers
      this.globalHandlers.forEach((handler) => handler(event));
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  subscribe(eventType: string, handler: EventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(eventType)?.delete(handler);
    };
  }

  subscribeAll(handler: EventHandler): () => void {
    this.globalHandlers.add(handler);
    return () => {
      this.globalHandlers.delete(handler);
    };
  }

  send(eventType: string, data: any): void {
    if (this.socket) {
      this.socket.emit(eventType, data);
    }
  }

  get isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const wsService = new WebSocketService();
export default wsService;

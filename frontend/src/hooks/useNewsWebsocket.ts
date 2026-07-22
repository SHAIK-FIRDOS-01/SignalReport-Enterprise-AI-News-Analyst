import { useState, useEffect } from 'react';

export function useNewsWebsocket(url: string = 'ws://localhost:8001/ws/alerts') {
  const [alert, setAlert] = useState<{message: string, type: string, count: number} | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: any;

    const connect = () => {
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('Connected to News Alerts WebSocket');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setAlert(data);
          
          // Clear alert after 5 seconds
          setTimeout(() => {
            setAlert(null);
          }, 5000);
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket closed, attempting to reconnect...');
        reconnectTimeout = setTimeout(connect, 3000);
      };
      
      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        ws.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) {
        ws.close();
      }
    };
  }, [url]);

  return { alert };
}

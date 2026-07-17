import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

const TERMINAL = new Set(['completed', 'failed', 'awaiting_approval']);

export function useJobPoller(jobId, interval = 2000) {
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) return;

    setError(null);
    setResult(null);

    const poll = async () => {
      try {
        const s = await api.getStatus(jobId);
        setStatus(s);

        if (TERMINAL.has(s.status)) {
          stopPolling();
          if (s.status === 'completed' || s.status === 'awaiting_approval') {
            try {
              const r = await api.getResult(jobId);
              setResult(r);
            } catch {
              // result not ready yet for awaiting_approval — that's okay
            }
          }
        }
      } catch (e) {
        setError(e.message);
        stopPolling();
      }
    };

    poll(); // immediate first poll
    timerRef.current = setInterval(poll, interval);

    return stopPolling;
  }, [jobId, interval, stopPolling]);

  return { status, result, error, stopPolling };
}

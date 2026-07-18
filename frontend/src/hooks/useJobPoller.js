import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

const STOP_POLLING = new Set(['completed', 'failed']);
const FETCH_RESULT_ON = new Set(['completed', 'awaiting_approval']);

export function useJobPoller(jobId, interval = 2000) {
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);
  const resultFetchedForRef = useRef(null);

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
    resultFetchedForRef.current = null;

    const poll = async () => {
      try {
        const s = await api.getStatus(jobId);
        setStatus(s);

        if (STOP_POLLING.has(s.status)) {
          stopPolling();
        }

        // awaiting_approval is not a stopping point — after the user
        // approves/rejects, the job keeps moving (summarizing -> completed),
        // so polling must continue. Only (re-)fetch the result when the
        // status actually changes, to avoid hammering the endpoint every tick.
        if (FETCH_RESULT_ON.has(s.status) && resultFetchedForRef.current !== s.status) {
          resultFetchedForRef.current = s.status;
          try {
            const r = await api.getResult(jobId);
            setResult(r);
          } catch {
            // result not ready yet for awaiting_approval — that's okay
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

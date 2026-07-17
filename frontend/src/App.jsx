import { useState, useCallback } from 'react';
import SearchForm from './components/SearchForm';
import AgentTimeline from './components/AgentTimeline';
import ApprovalPanel from './components/ApprovalPanel';
import ResultView from './components/ResultView';
import JobHistory from './components/JobHistory';
import { api } from './api/client';
import { useJobPoller } from './hooks/useJobPoller';
import { BrainCircuit } from 'lucide-react';

export default function App() {
  const [jobId, setJobId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const { status, result, error: pollError } = useJobPoller(jobId);

  const handleSubmit = useCallback(async (data) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await api.submitJob(data);
      setJobId(res.job_id);
    } catch (e) {
      setSubmitError(e.message);
    } finally {
      setSubmitting(false);
    }
  }, []);

  const handleApprove = useCallback(async (approved, feedback) => {
    if (!jobId) return;
    try {
      await api.approveJob(jobId, approved, feedback);
      // Re-trigger polling by setting the same jobId
      setJobId((prev) => prev);
      // Force a fresh poll cycle
      window.location.reload();
    } catch (e) {
      setSubmitError(e.message);
    }
  }, [jobId]);

  const handleSelectJob = useCallback((id) => {
    setJobId(id);
    setSubmitError(null);
  }, []);

  const isRunning = status && !['completed', 'failed'].includes(status.status);
  const needsApproval = status?.status === 'awaiting_approval';
  const isComplete = status?.status === 'completed';

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <BrainCircuit size={28} />
          <div>
            <h1>Research Assistant</h1>
            <p className="tagline">Multi-agent AI research pipeline</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="content-area">
          <SearchForm onSubmit={handleSubmit} loading={submitting || isRunning} />

          {(submitError || pollError) && (
            <div className="error-bar">
              {submitError || pollError}
            </div>
          )}

          {status && (
            <AgentTimeline
              status={status}
              traces={status.traces || result?.traces}
            />
          )}

          {needsApproval && (
            <ApprovalPanel result={result} onApprove={handleApprove} />
          )}

          {isComplete && result && (
            <ResultView result={result} />
          )}

          {!jobId && !submitting && (
            <div className="empty-state">
              <BrainCircuit size={48} strokeWidth={1} />
              <h2>Ask a research question</h2>
              <p>
                Three AI agents — a planner, researcher, and summarizer — will 
                collaborate to find, verify, and synthesize answers from multiple sources.
              </p>
              <div className="feature-list">
                <span>Structured research plans</span>
                <span>Multi-source synthesis</span>
                <span>Human-in-the-loop review</span>
                <span>Guardrail checks</span>
                <span>Full agent tracing</span>
              </div>
            </div>
          )}
        </div>

        <aside className="sidebar">
          <JobHistory onSelect={handleSelectJob} currentJobId={jobId} />
        </aside>
      </main>
    </div>
  );
}

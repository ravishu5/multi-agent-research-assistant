import { CheckCircle, Clock, AlertCircle, Loader } from 'lucide-react';

const STATUS_FLOW = ['pending', 'planning', 'researching', 'awaiting_approval', 'summarizing', 'completed'];

const STEP_LABELS = {
  pending: 'Queued',
  planning: 'Planning',
  researching: 'Researching',
  awaiting_approval: 'Review',
  summarizing: 'Summarizing',
  completed: 'Done',
  failed: 'Failed',
};

export default function AgentTimeline({ status, traces }) {
  const currentStatus = status?.status || 'pending';
  const currentIdx = STATUS_FLOW.indexOf(currentStatus);

  return (
    <div className="timeline">
      <div className="timeline-steps">
        {STATUS_FLOW.map((step, i) => {
          const isDone = i < currentIdx || currentStatus === 'completed';
          const isActive = i === currentIdx && currentStatus !== 'completed' && currentStatus !== 'failed';
          const isFailed = currentStatus === 'failed' && i === currentIdx;

          return (
            <div
              key={step}
              className={`timeline-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''} ${isFailed ? 'failed' : ''}`}
            >
              <div className="step-dot">
                {isDone && <CheckCircle size={16} />}
                {isActive && <Loader size={16} className="spin" />}
                {isFailed && <AlertCircle size={16} />}
                {!isDone && !isActive && !isFailed && <Clock size={16} />}
              </div>
              <span className="step-label">{STEP_LABELS[step]}</span>
            </div>
          );
        })}
      </div>

      {status?.progress && (
        <p className="timeline-progress">{status.progress}</p>
      )}

      {traces && traces.length > 0 && (
        <div className="trace-log">
          <h4>Agent Trace Log</h4>
          {traces.map((t, i) => (
            <div key={i} className="trace-entry">
              <span className="trace-agent">{t.agent}</span>
              <span className="trace-action">{t.action}</span>
              <span className="trace-duration">{t.duration_ms?.toFixed(0)}ms</span>
              {t.token_usage && Object.keys(t.token_usage).length > 0 && (
                <span className="trace-tokens">
                  {t.token_usage.input || 0}→{t.token_usage.output || 0} tok
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

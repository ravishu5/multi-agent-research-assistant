import { useState, useEffect } from 'react';
import { History, Clock, CheckCircle, AlertCircle, Loader, PauseCircle } from 'lucide-react';
import { api } from '../api/client';

const STATUS_ICONS = {
  completed: CheckCircle,
  failed: AlertCircle,
  awaiting_approval: PauseCircle,
};

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function JobHistory({ onSelect, currentJobId }) {
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.listJobs();
        setJobs(data);
      } catch {
        // ignore
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [currentJobId]);

  if (jobs.length === 0) return null;

  return (
    <div className="job-history">
      <h4><History size={14} /> Recent Jobs</h4>
      <div className="job-list">
        {jobs.slice(0, 10).map((job) => {
          const Icon = STATUS_ICONS[job.status] || Loader;
          const isActive = job.job_id === currentJobId;
          return (
            <button
              key={job.job_id}
              className={`job-item ${isActive ? 'active' : ''} status-${job.status}`}
              onClick={() => onSelect(job.job_id)}
            >
              <Icon size={12} className={job.status === 'pending' || job.status === 'planning' || job.status === 'researching' || job.status === 'summarizing' ? 'spin' : ''} />
              <span className="job-query">{job.query?.slice(0, 50)}{job.query?.length > 50 ? '...' : ''}</span>
              <span className="job-time">{timeAgo(job.created_at)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

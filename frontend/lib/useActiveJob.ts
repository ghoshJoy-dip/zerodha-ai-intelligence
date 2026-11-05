"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { getJobAudit, getJobResult, type AuditResult, type JobResult } from "./api";

function subscribeToActiveJob(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("active-job-storage", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("active-job-storage", callback);
  };
}

function getActiveJobSnapshot() {
  return window.localStorage.getItem("activeJobId");
}

function getServerJobSnapshot() {
  return null;
}

export function useActiveJobId() {
  return useSyncExternalStore(
    subscribeToActiveJob,
    getActiveJobSnapshot,
    getServerJobSnapshot,
  );
}

export function useActiveJobData() {
  const jobId = useActiveJobId();
  const [job, setJob] = useState<JobResult | null>(null);
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [error, setError] = useState("");
  const [loadedJobId, setLoadedJobId] = useState<string | null>(null);

  useEffect(() => {
    if (jobId === null) return;
    const activeJobId: string = jobId;

    let active = true;
    async function load() {
      try {
        const [jobResult, auditResult] = await Promise.all([
          getJobResult(activeJobId),
          getJobAudit(activeJobId),
        ]);
        if (!active) return;
        setJob(jobResult);
        setAudit(auditResult);
        setLoadedJobId(activeJobId);
        setError("");
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Could not load active job.");
          setLoadedJobId(activeJobId);
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [jobId]);

  return { jobId, job, audit, error, loading: Boolean(jobId) && loadedJobId !== jobId };
}

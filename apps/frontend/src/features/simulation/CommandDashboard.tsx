import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { sendRuntimeCommand } from "@/lib/api/simulation";
import { ApiClientError } from "@/lib/api/client";

interface CommandDashboardProps {
  simulationId: string;
  onRequireAdminKey: () => void;
}

export function CommandDashboard({ simulationId, onRequireAdminKey }: CommandDashboardProps) {
  const [type, setType] = useState("close_exit");
  const [exitId, setExitId] = useState("");
  const [targetExit, setTargetExit] = useState("");
  const [doorId, setDoorId] = useState("");
  const [message, setMessage] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      sendRuntimeCommand(simulationId, {
        type,
        exit_id: exitId || undefined,
        target_exit: targetExit || undefined,
        door_id: doorId || undefined,
        message: message || undefined,
      }),
    onError: (error) => {
      if (error instanceof ApiClientError && (error.status === 401 || error.status === 403)) {
        onRequireAdminKey();
      }
    },
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate();
  };

  return (
    <section className="panel space-y-4">
      <h3 className="section-title">Runtime Commands</h3>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={submit}>
        <label>
          <span className="label">Command Type</span>
          <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="close_exit">Close Exit</option>
            <option value="redirect_crowd">Redirect Crowd</option>
            <option value="trigger_fire_door">Trigger Fire Door</option>
            <option value="emergency_announcement">Emergency Announcement</option>
          </select>
        </label>

        <label>
          <span className="label">Exit ID</span>
          <input className="input" value={exitId} onChange={(e) => setExitId(e.target.value)} placeholder="for close_exit" />
        </label>

        <label>
          <span className="label">Target Exit</span>
          <input className="input" value={targetExit} onChange={(e) => setTargetExit(e.target.value)} placeholder="for redirect_crowd" />
        </label>

        <label>
          <span className="label">Door ID</span>
          <input className="input" value={doorId} onChange={(e) => setDoorId(e.target.value)} placeholder="for trigger_fire_door" />
        </label>

        <label className="sm:col-span-2">
          <span className="label">Announcement</span>
          <input
            className="input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="for emergency_announcement"
          />
        </label>

        <div className="sm:col-span-2">
          <button type="submit" className="btn-secondary" disabled={!simulationId || mutation.isPending}>
            Send Command
          </button>
        </div>
      </form>

      {mutation.isSuccess && <p className="text-sm text-emerald-300">Command accepted.</p>}
      {mutation.error && <p className="text-sm text-rose-300">{String((mutation.error as Error).message)}</p>}
    </section>
  );
}

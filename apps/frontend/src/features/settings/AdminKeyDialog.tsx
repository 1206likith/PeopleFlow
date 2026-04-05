import { FormEvent, useEffect, useState } from "react";
import { useSessionStore } from "@/lib/state/sessionStore";

interface AdminKeyDialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
}

export function AdminKeyDialog({
  open,
  onClose,
  title = "Admin key required",
  description = "Mutation APIs require X-Admin-Key. Enter it once for this session.",
}: AdminKeyDialogProps) {
  const storedKey = useSessionStore((state) => state.adminKey);
  const setAdminKey = useSessionStore((state) => state.setAdminKey);
  const [value, setValue] = useState(storedKey);

  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setValue(storedKey);
    }
  }, [open, storedKey]);

  if (!open) {
    return null;
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAdminKey(value.trim());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 px-4 backdrop-blur-sm">
      <form className="w-full max-w-md rounded-[20px] border border-white/10 bg-[rgba(6,9,18,0.96)] p-6 shadow-[0_30px_90px_rgba(0,0,0,0.4)]" onSubmit={submit}>
        <p className="label">Admin Session</p>
        <h3 className="section-title mt-3">{title}</h3>
        <p className="mt-2 text-sm text-mist/70">{description}</p>

        <label className="mt-4 block text-sm text-mist/80" htmlFor="admin-key-input">
          Admin key
        </label>
        <input
          id="admin-key-input"
          className="input"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Enter X-Admin-Key"
          autoFocus
        />

        <div className="mt-5 flex items-center justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={!value.trim()}>
            Save for session
          </button>
        </div>
      </form>
    </div>
  );
}

import { FormEvent, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadFloorPlan } from "@/lib/api/designer";
import { FloorPlanMetadata } from "@/lib/api/types";
import { ApiClientError } from "@/lib/api/client";
import { ErrorPanel } from "@/components/common/ErrorPanel";

interface FloorPlanUploadPanelProps {
  onUploaded: (payload: FloorPlanMetadata) => void;
  onRequireAdminKey: () => void;
}

export function FloorPlanUploadPanel({ onUploaded, onRequireAdminKey }: FloorPlanUploadPanelProps) {
  const [file, setFile] = useState<File | undefined>(undefined);
  const [buildingName, setBuildingName] = useState("Main Building");
  const [floorNumber, setFloorNumber] = useState(1);
  const [detectorMode, setDetectorMode] = useState<"auto" | "traditional" | "semantic">("auto");

  const defaultMetadata = useMemo(
    () => ({
      buildingName,
      floors: [{ floorNumber, name: `Floor ${floorNumber}`, exits: [] }],
      processingOptions: { mode: detectorMode },
    }),
    [buildingName, detectorMode, floorNumber],
  );

  const mutation = useMutation({
    mutationFn: () => uploadFloorPlan({ file, metadata: defaultMetadata }),
    onSuccess: (payload) => {
      const previewImageUrl =
        file && typeof window !== "undefined" && file.type.startsWith("image/")
          ? window.URL.createObjectURL(file)
          : undefined;
      onUploaded(
        previewImageUrl
          ? ({
              ...payload,
              preview_image_url: previewImageUrl,
            } as FloorPlanMetadata)
          : payload,
      );
    },
    onError: (error) => {
      if (error instanceof ApiClientError && (error.code === "admin_key_missing" || error.code === "admin_key_invalid")) {
        onRequireAdminKey();
      }
    },
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate();
  };

  return (
    <section className="panel">
      <h3 className="section-title">Upload Floor Plan</h3>
      <p className="mt-2 text-sm text-mist/70">
        Supports image upload or JSON metadata payload. If no file is selected, metadata-only upload still works.
      </p>

      <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={submit}>
        <label className="block">
          <span className="label">Building Name</span>
          <input className="input" value={buildingName} onChange={(e) => setBuildingName(e.target.value)} />
        </label>

        <label className="block">
          <span className="label">Floor Number</span>
          <input
            className="input"
            type="number"
            min={1}
            value={floorNumber}
            onChange={(e) => setFloorNumber(Number(e.target.value || 1))}
          />
        </label>

        <label className="block sm:col-span-2">
          <span className="label">File (image/json/pdf)</span>
          <input
            className="input"
            type="file"
            accept=".json,.jpg,.jpeg,.png,.gif,.webp,.pdf"
            onChange={(event) => setFile(event.target.files?.[0])}
          />
        </label>

        <label className="block sm:col-span-2">
          <span className="label">Detection Mode</span>
          <select
            className="input"
            value={detectorMode}
            onChange={(e) => setDetectorMode(e.target.value as "auto" | "traditional" | "semantic")}
          >
            <option value="auto">Auto (recommended)</option>
            <option value="traditional">Traditional</option>
            <option value="semantic">Semantic</option>
          </select>
        </label>

        <div className="sm:col-span-2">
          <button type="submit" className="btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Uploading..." : "Upload Floor Plan"}
          </button>
        </div>
      </form>

      {mutation.isSuccess && <p className="mt-3 text-sm text-emerald-300">Floor plan uploaded successfully.</p>}
      {mutation.error && <div className="mt-4"><ErrorPanel error={mutation.error} /></div>}
    </section>
  );
}

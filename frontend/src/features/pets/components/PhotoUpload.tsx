import { useRef, useState } from "react";
import { useUploadPetPhoto, type PhotoUploadResult } from "@/features/pets/api";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/feedback";

interface PhotoUploadProps {
  onUploaded: (result: PhotoUploadResult) => void;
  uploaded: PhotoUploadResult | null;
}

/**
 * Pet-photo upload with the YOLOv8 gatekeeper UX: a non-pet photo gets a 422
 * "no pet detected" response — never a ban — and the user can pick another file.
 */
export function PhotoUpload({ onUploaded, uploaded }: PhotoUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadPetPhoto();
  const [error, setError] = useState<ApiError | null>(null);
  const [imageFailed, setImageFailed] = useState(false);

  const pick = (file: File | undefined) => {
    if (!file) return;
    setError(null);
    setImageFailed(false);
    upload.mutate(file, {
      onSuccess: (result) => onUploaded(result),
      onError: (e) => setError(e instanceof ApiError ? e : new ApiError(e as never)),
    });
  };

  const noPet = error?.status === 422 && error.code === "no_pet_detected";
  const src = uploaded?.thumb_url || uploaded?.url;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        aria-label="Choose a pet photo"
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {/* Single photo display area — one state at a time */}
      <div className="photo-frame" style={{ borderRadius: 20, border: "1px solid var(--color-line)", maxWidth: 360 }}>
        {upload.isPending ? (
          // Uploading — show skeleton inside the frame, not "No photo uploaded yet"
          <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <Skeleton style={{ aspectRatio: "4 / 3", borderRadius: 20 }} />
            <p className="t-small" style={{ color: "var(--color-muted)", margin: 0 }}>
              Checking the photo for a pet…
            </p>
          </div>
        ) : uploaded && imageFailed ? (
          <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <span style={{ color: "var(--color-muted)", fontSize: 14 }}>Could not load photo</span>
            <p className="t-small" style={{ color: "var(--color-muted)", margin: 0 }}>
              Pick another photo below
            </p>
          </div>
        ) : uploaded && src ? (
          <img
            src={src}
            alt="Uploaded pet preview"
            onError={() => setImageFailed(true)}
            style={{ width: "100%", aspectRatio: "4 / 3", objectFit: "cover", display: "block" }}
          />
        ) : (
          <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-muted)" }}>
            No photo uploaded yet
          </div>
        )}
      </div>

      <div className="btn-row">
        <Button
          type="button"
          variant={uploaded ? "secondary" : "primary"}
          disabled={upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {upload.isPending ? "Checking…" : uploaded ? "Choose a different photo" : "Choose a photo"}
        </Button>
        {uploaded && !imageFailed && <span className="badge badge--outreach">Pet detected ✓</span>}
      </div>

      {noPet && (
        <div className="error-box" role="alert" data-testid="no-pet-error">
          <p style={{ fontWeight: 600 }}>{error.message}</p>
          <p style={{ marginTop: 4 }}>
            No strikes, no bans — just pick another photo.
            {error.detectedLabels && error.detectedLabels.length > 0 && (
              <> Detected instead: {error.detectedLabels.join(", ")}.</>
            )}
          </p>
        </div>
      )}
      {error && !noPet && (
        <div className="error-box" role="alert">
          {error.message}
        </div>
      )}
    </div>
  );
}

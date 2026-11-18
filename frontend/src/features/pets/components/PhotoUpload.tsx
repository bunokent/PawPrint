import { useRef, useState, useEffect } from "react";
import { useUploadPetPhoto, type PhotoUploadResult } from "@/features/pets/api";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/feedback";

// Extend PhotoUploadResult locally for the local URL preview
interface LocalPhotoUploadResult extends PhotoUploadResult {
  localUrl?: string;
}

interface PhotoUploadProps {
  onUploaded: (result: LocalPhotoUploadResult) => void;
  uploaded: LocalPhotoUploadResult | null;
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

  // Effect to clean up local object URL when the component unmounts or uploaded changes
  useEffect(() => {
    if (uploaded?.localUrl) {
      return () => URL.revokeObjectURL(uploaded.localUrl);
    }
  }, [uploaded?.localUrl]);

  const pick = (file: File | undefined) => {
    if (!file) return;
    const localUrl = URL.createObjectURL(file);

    setError(null);
    setImageFailed(false);

    // Pass localUrl to ensure persistence across navigation
    upload.mutate(file, {
      onSuccess: (result) => onUploaded({ ...result, localUrl }),
      onError: (e) => setError(e instanceof ApiError ? e : new ApiError(e as never)),
    });
  };

  const noPet = error?.status === 422 && error.code === "no_pet_detected";
  // Prioritize local URL for preview persistence
  const src = uploaded?.localUrl || uploaded?.thumb_url || uploaded?.url;
  const isPending = upload.isPending;

  // Drag and Drop Handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      pick(e.dataTransfer.files[0]);
    }
  };

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
      <div
        className="photo-frame"
        style={{ borderRadius: 20, border: "1px solid var(--color-line)", maxWidth: 360 }}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isPending ? (
          // Uploading — show skeleton inside the frame
          <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <Skeleton style={{ aspectRatio: "4 / 3", borderRadius: 20 }} />
            <p className="t-small" style={{ color: "var(--color-muted)", margin: 0 }}>
              Checking the photo for a pet…
            </p>
          </div>
        ) : uploaded && imageFailed ? (
          // Image failed to load (e.g., expired signed URL)
          <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <span style={{ color: "var(--color-muted)", fontSize: 14 }}>Could not load photo</span>
            <p className="t-small" style={{ color: "var(--color-muted)", margin: 0 }}>
              Pick another photo below
            </p>
          </div>
        ) : uploaded && src ? (
          // Image loaded successfully
          <img
            src={src}
            alt="Uploaded pet preview"
            onError={() => setImageFailed(true)}
            style={{ width: "100%", aspectRatio: "4 / 3", objectFit: "cover", display: "block" }}
          />
        ) : (
          // No photo uploaded yet - Drag and drop zone
          <div
            style={{ 
              width: "100%", 
              height: "100%", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center", 
              color: "var(--color-muted)",
              border: "2px dashed var(--color-line)",
              borderRadius: 20
            }}
          >
            Drag & drop a photo here or click to choose
          </div>
        )}
      </div>

      <div className="btn-row">
        <Button
          type="button"
          variant={uploaded ? "secondary" : "primary"}
          disabled={isPending}
          onClick={() => inputRef.current?.click()}
        >
          {isPending ? "Checking…" : uploaded ? "Choose a different photo" : "Choose a photo"}
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
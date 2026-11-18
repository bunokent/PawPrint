import { useEffect, useRef, useState } from "react";
import { Check, ImagePlus, LoaderCircle } from "lucide-react";
import { useUploadPetPhoto, type PhotoUploadResult } from "@/features/pets/api";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";

// Extend PhotoUploadResult locally for the local URL preview
interface LocalPhotoUploadResult extends PhotoUploadResult {
  localUrl?: string;
}

interface PhotoUploadProps {
  onUploaded: (result: LocalPhotoUploadResult) => void;
  uploaded: LocalPhotoUploadResult | null;
}

const UPLOAD_STAGES = [
  { id: "uploading", label: "Uploading photo", shortLabel: "Upload", detail: "Sending your photo over a secure connection" },
  { id: "scanning", label: "Scanning photo", shortLabel: "Scan", detail: "Reading the image and preparing it for pet detection" },
  { id: "detecting", label: "Detecting your pet", shortLabel: "Detect", detail: "YOLO-World is looking for a pet in your photo" },
  { id: "saving", label: "Saving securely", shortLabel: "Save", detail: "Removing metadata and preparing your private preview" },
] as const;

type UploadStage = (typeof UPLOAD_STAGES)[number]["id"];

/**
 * Pet-photo upload with the YOLO-World gatekeeper UX: a non-pet photo gets a 422
 * "no pet detected" response — never a ban — and the user can pick another file.
 */
export function PhotoUpload({ onUploaded, uploaded }: PhotoUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingUrlRef = useRef<string | null>(null);
  const upload = useUploadPetPhoto();
  const [error, setError] = useState<ApiError | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [pendingPreview, setPendingPreview] = useState<string | null>(null);
  const [stage, setStage] = useState<UploadStage>("uploading");
  const [uploadProgress, setUploadProgress] = useState(0);
  const isPending = upload.isPending;

  // Effect to clean up local object URL when the component unmounts or uploaded changes
  useEffect(() => {
    const localUrl = uploaded?.localUrl;
    if (localUrl) {
      return () => URL.revokeObjectURL(localUrl);
    }
  }, [uploaded?.localUrl]);

  useEffect(() => () => {
    if (pendingUrlRef.current) URL.revokeObjectURL(pendingUrlRef.current);
  }, []);

  // The endpoint is synchronous, so network progress is exact and the remaining
  // labels follow the server's scan → detect → save pipeline while it responds.
  useEffect(() => {
    if (!isPending || (stage !== "scanning" && stage !== "detecting")) return;
    const nextStage: UploadStage = stage === "scanning" ? "detecting" : "saving";
    const timer = window.setTimeout(() => setStage(nextStage), stage === "scanning" ? 800 : 1000);
    return () => window.clearTimeout(timer);
  }, [isPending, stage]);

  const pick = (file: File | undefined) => {
    if (!file || isPending) return;
    if (pendingUrlRef.current) URL.revokeObjectURL(pendingUrlRef.current);
    const localUrl = URL.createObjectURL(file);
    pendingUrlRef.current = localUrl;

    setError(null);
    setImageFailed(false);
    setPendingPreview(localUrl);
    setStage("uploading");
    setUploadProgress(0);

    upload.mutate(
      {
        file,
        onProgress: (percentage) => {
          setUploadProgress(percentage);
          if (percentage === 100) {
            setStage((current) => current === "uploading" ? "scanning" : current);
          }
        },
      },
      {
        onSuccess: (result) => {
          // Ownership of the object URL passes to the controlled uploaded result.
          pendingUrlRef.current = null;
          onUploaded({ ...result, localUrl });
        },
        onError: (e) => {
          URL.revokeObjectURL(localUrl);
          if (pendingUrlRef.current === localUrl) pendingUrlRef.current = null;
          setPendingPreview(null);
          setError(e instanceof ApiError ? e : new ApiError(e as never));
        },
      },
    );
  };

  const noPet = error?.status === 422 && error.code === "no_pet_detected";
  const src = uploaded?.localUrl || uploaded?.thumb_url || uploaded?.url;
  const currentStageIndex = UPLOAD_STAGES.findIndex((item) => item.id === stage);
  const currentStage = UPLOAD_STAGES[currentStageIndex];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isPending) e.dataTransfer.dropEffect = "copy";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (!isPending) pick(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="photo-upload" aria-busy={isPending}>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="photo-upload__input"
        aria-label="Choose a pet photo"
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      <div
        className={`photo-frame photo-upload__frame${isDragging ? " photo-upload__frame--dragging" : ""}${isPending ? " photo-upload__frame--pending" : ""}`}
        onDragEnter={(e) => {
          e.preventDefault();
          if (!isPending) setIsDragging(true);
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setIsDragging(false);
        }}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isPending ? (
          <div className="photo-upload__processing">
            {pendingPreview && <img className="photo-upload__preview" src={pendingPreview} alt="" aria-hidden="true" />}
            <div className="photo-upload__scrim" aria-hidden="true" />
            <div className="photo-upload__scan-line" aria-hidden="true" />

            <div className="photo-upload__status-card">
              <div className="photo-upload__status-heading">
                <span className="photo-upload__spinner" aria-hidden="true">
                  <LoaderCircle size={22} strokeWidth={2} />
                </span>
                <div>
                  <p className="photo-upload__status-title" role="status" aria-live="polite" aria-atomic="true">
                    {currentStage.label}
                  </p>
                  <p className="photo-upload__status-detail">{currentStage.detail}</p>
                </div>
              </div>

              <div className="photo-upload__progress-meta">
                <span>Photo check</span>
                <span>{stage === "uploading" ? `${uploadProgress}%` : `Step ${currentStageIndex + 1} of ${UPLOAD_STAGES.length}`}</span>
              </div>
              <div
                className="photo-upload__progress"
                role="progressbar"
                aria-label="Photo upload progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={stage === "uploading" ? uploadProgress : undefined}
                aria-valuetext={stage === "uploading" ? `${uploadProgress}% uploaded` : currentStage.label}
              >
                <span
                  className={`photo-upload__progress-fill${stage === "uploading" ? "" : " photo-upload__progress-fill--indeterminate"}`}
                  style={stage === "uploading" ? { width: `${Math.max(3, uploadProgress)}%` } : undefined}
                />
              </div>

              <ol className="photo-upload__steps" aria-hidden="true">
                {UPLOAD_STAGES.map((item, index) => (
                  <li
                    key={item.id}
                    className={`photo-upload__step${index === currentStageIndex ? " photo-upload__step--current" : ""}${index < currentStageIndex ? " photo-upload__step--done" : ""}`}
                  >
                    <span className="photo-upload__step-marker">
                      {index < currentStageIndex ? <Check size={12} strokeWidth={3} /> : index + 1}
                    </span>
                    <span>{item.shortLabel}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        ) : uploaded && imageFailed ? (
          <div className="photo-upload__message">
            <span>Could not load photo</span>
            <p className="t-small">Pick another photo below</p>
          </div>
        ) : uploaded && src ? (
          <img
            className="photo-upload__uploaded-image"
            src={src}
            alt="Uploaded pet preview"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <button className="photo-upload__empty" type="button" onClick={() => inputRef.current?.click()}>
            <span className="photo-upload__icon" aria-hidden="true">
              <ImagePlus size={30} strokeWidth={1.8} />
            </span>
            <span className="photo-upload__empty-title">Drop your pet’s photo here</span>
            <span className="photo-upload__empty-action">or click to browse from your device</span>
            <span className="photo-upload__empty-hint">Choose a clear, well-lit photo so people can recognise your pet.</span>
          </button>
        )}
      </div>

      <div className="btn-row">
        <Button
          type="button"
          variant={uploaded ? "secondary" : "primary"}
          disabled={isPending}
          onClick={() => inputRef.current?.click()}
        >
          {isPending ? "Processing…" : uploaded ? "Choose a different photo" : "Choose a photo"}
        </Button>
        {uploaded && !imageFailed && !isPending && <span className="badge badge--outreach">Pet detected ✓</span>}
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

import { useState } from "react";

interface AvatarProps {
  /** Signed URL of the stored profile picture ("" / null when none). */
  src?: string | null;
  /** Used for the alt text and the fallback initial. */
  name: string;
  size?: number;
  /** When true the picture is decorative (the name sits right next to it) → alt="". */
  decorative?: boolean;
}

/** Round profile picture with an initial-letter fallback (also on image error). */
export function Avatar({ src, name, size = 40, decorative = false }: AvatarProps) {
  const [failed, setFailed] = useState(false);
  const initial = (name.trim()[0] ?? "?").toUpperCase();
  if (!src || failed) {
    return (
      <span
        className="avatar avatar--fallback"
        style={{ width: size, height: size, fontSize: Math.round(size * 0.45) }}
        aria-hidden={decorative ? true : undefined}
        role={decorative ? undefined : "img"}
        aria-label={decorative ? undefined : `${name}'s profile picture`}
      >
        {initial}
      </span>
    );
  }
  return (
    <img
      className="avatar"
      src={src}
      alt={decorative ? "" : `${name}'s profile picture`}
      style={{ width: size, height: size }}
      onError={() => setFailed(true)}
    />
  );
}

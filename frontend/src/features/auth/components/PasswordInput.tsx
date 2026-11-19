import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";
import { IconInput } from "@/components/ui/field";

/**
 * Password field with a lock icon and an eye toggle that switches the input
 * between `password` and `text`. The toggle is a real button with an
 * accessible name ("Show password" / "Hide password") and pressed state.
 */
export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  return (
    <IconInput
      type={show ? "text" : "password"}
      icon={<Lock size={18} strokeWidth={1.8} />}
      trailing={
        <button
          type="button"
          className="input-eye"
          aria-label={show ? "Hide password" : "Show password"}
          aria-pressed={show}
          onClick={() => setShow((v) => !v)}
        >
          {show ? <EyeOff size={18} strokeWidth={1.8} aria-hidden="true" /> : <Eye size={18} strokeWidth={1.8} aria-hidden="true" />}
        </button>
      }
      {...props}
    />
  );
}

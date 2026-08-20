import { MouseEvent, useEffect, useState } from "react";
import TextField from "@mui/material/TextField";

function hrefFor(url: string): string | null {
  const raw = url.trim();
  if (!raw || /[\u0000-\u001F\u007F]/.test(raw)) return null;
  if (/^(javascript|data|vbscript|file):/i.test(raw)) return null;
  try {
    const withProtocol = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
    const parsed = new URL(withProtocol);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    if (parsed.username || parsed.password) return null;
    if (!parsed.hostname) return null;
    return parsed.href;
  } catch {
    return null;
  }
}

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export default function OpenableUrlField({ value, onChange }: Props) {
  const [hovered, setHovered] = useState(false);
  const [modifier, setModifier] = useState(false);
  const href = hrefFor(value);
  const clickable = Boolean(href && hovered && modifier);

  useEffect(() => {
    function sync(event: KeyboardEvent) {
      setModifier(event.ctrlKey || event.metaKey);
    }
    function clear() {
      setModifier(false);
    }
    window.addEventListener("keydown", sync);
    window.addEventListener("keyup", sync);
    window.addEventListener("blur", clear);
    return () => {
      window.removeEventListener("keydown", sync);
      window.removeEventListener("keyup", sync);
      window.removeEventListener("blur", clear);
    };
  }, []);

  function openIfModifier(event: MouseEvent<HTMLDivElement>) {
    if (!(event.ctrlKey || event.metaKey) || !href) return;
    event.preventDefault();
    window.open(href, "_blank", "noopener,noreferrer");
  }

  return (
    <TextField
      label="URL"
      type="url"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={openIfModifier}
      onContextMenu={openIfModifier}
      title={href ? "Hold Ctrl (⌘ on Mac) while hovering, then click to open in a new tab" : undefined}
      sx={
        clickable
          ? {
              "& .MuiInputBase-input": {
                cursor: "pointer",
                color: "primary.main",
                textDecoration: "underline",
              },
            }
          : undefined
      }
    />
  );
}

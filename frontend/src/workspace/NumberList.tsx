import { useState } from "react";
export default function NumberList({
  value,
  onChange,
  label,
  placeholder,
}: {
  value: number[] | undefined;
  onChange: (value: number[] | undefined) => void;
  label: string;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <input
      aria-label={label}
      inputMode="text"
      placeholder={placeholder}
      value={draft ?? value?.join(", ") ?? ""}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => {
        if (draft === null) return;
        const text = draft.trim();
        onChange(
          text
            ? text.split(",").map((v) => (v.trim() ? Number(v) : NaN))
            : undefined,
        );
        setDraft(null);
      }}
    />
  );
}

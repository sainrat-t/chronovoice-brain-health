// New person: a minimal form, then straight to the first session (live demo path).
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Card, ErrorNote } from "../components/ui";
import { buttonStyles } from "../lib/styles";

export function NewPerson() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const person = await api.createPerson({
        display_name: name.trim(),
        birth_year: birthYear ? Number(birthYear) : null,
        language: "eng",
      });
      navigate(`/people/${person.person_id}/new-session`);
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error(String(reason)));
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">New person</h1>
      <Card>
        <form onSubmit={submit} className="space-y-5">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Name or pseudonym</span>
            <input
              required
              maxLength={120}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2"
              autoFocus
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Year of birth</span>
            <input
              type="number"
              min={1900}
              max={2030}
              value={birthYear}
              onChange={(event) => setBirthYear(event.target.value)}
              className="mt-1.5 w-40 rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Language</span>
            <select
              disabled
              className="mt-1.5 block w-40 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2"
            >
              <option>English</option>
            </select>
            <span className="mt-1 block text-xs text-slate-500">
              The analysis is designed for any language; English is the only one available in
              this prototype.
            </span>
          </label>
          {error && <ErrorNote error={error} />}
          <button type="submit" className={buttonStyles.primary} disabled={!name.trim() || saving}>
            Create and record a first session
          </button>
        </form>
      </Card>
    </div>
  );
}

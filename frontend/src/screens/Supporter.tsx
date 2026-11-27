import { useState, type FormEvent } from "react";
import { Check, Copy, UserRound, X } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { Notice } from "../components/common";
import type { Supporter } from "../types";
import { useLoad } from "../useLoad";

export function SupporterScreen() {
  const { data: supporters, reload } = useLoad<Supporter[]>("/supporters");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<Supporter | null>(null);

  const link = (s: Supporter) => `${window.location.origin}/shared/${s.token}`;

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Γράψε το όνομα του ανθρώπου.");
      return;
    }
    try {
      await api.post("/supporters", { name: name.trim() });
      setName("");
      setError(null);
      setMessage("Έτοιμο. Στείλε τον σύνδεσμο μόνο σε αυτόν τον άνθρωπο.");
      reload();
    } catch (err) {
      setError(errorText(err));
    }
  };

  const revoke = async (s: Supporter) => {
    await api.del(`/supporters/${s.id}`).catch(() => undefined);
    setConfirm(null);
    setMessage(`Η πρόσβαση για «${s.name}» σταμάτησε.`);
    reload();
  };

  const copy = async (s: Supporter) => {
    try {
      await navigator.clipboard.writeText(link(s));
      setMessage("Ο σύνδεσμος αντιγράφηκε.");
    } catch {
      setMessage("Δεν έγινε αντιγραφή. Επίλεξε τον σύνδεσμο και αντίγραψέ τον.");
    }
  };

  if (confirm) {
    return (
      <Screen title="Σταμάτημα πρόσβασης" back={() => setConfirm(null)}>
        <p className="lead">Θέλεις να σταματήσεις την πρόσβαση για «{confirm.name}»;</p>
        <p>Ο σύνδεσμος δεν θα δουλεύει πια. Μπορείς να δώσεις νέα πρόσβαση όποτε θέλεις.</p>
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => revoke(confirm)}>
            <Check aria-hidden="true" />
            Ναι, σταμάτα την πρόσβαση
          </button>
          <button type="button" className="btn" onClick={() => setConfirm(null)}>
            <X aria-hidden="true" />
            Όχι, άφησέ τη
          </button>
        </div>
      </Screen>
    );
  }

  return (
    <Screen title="Υποστηρικτής" back="/settings">
      <p>Μπορείς να δείξεις την πρόοδό σου σε έναν άνθρωπο που εμπιστεύεσαι. Για παράδειγμα, σε κάποιον από τη Μονάδα Προσβασιμότητας ή από την οικογένειά σου.</p>
      <ul className="plain-list">
        <li>Θα βλέπει μόνο το επίπεδο βοήθειας και πόση βοήθεια χρειάστηκες σε κάθε μάθημα.</li>
        <li>Δεν θα βλέπει τις απαντήσεις σου.</li>
        <li>Μπορείς να σταματήσεις την πρόσβαση όποτε θέλεις.</li>
      </ul>
      {message && <Notice tone="success" icon={Check} live>{message}</Notice>}

      {supporters && supporters.length > 0 && (
        <section aria-labelledby="active-title">
          <h2 id="active-title">Ποιοι βλέπουν την πρόοδό σου</h2>
          <ul className="cards">
            {supporters.map((s) => (
              <li key={s.id} className="card">
                <UserRound aria-hidden="true" className="course-icon" />
                <div className="card-body">
                  <span className="card-title">{s.name}</span>
                  <span className="link-text">{link(s)}</span>
                  <div className="actions actions-row">
                    <button type="button" className="btn" onClick={() => copy(s)}>
                      <Copy aria-hidden="true" />
                      Αντίγραψε τον σύνδεσμο
                    </button>
                    <button type="button" className="btn btn-danger" onClick={() => setConfirm(s)}>
                      <X aria-hidden="true" />
                      Σταμάτα την πρόσβαση
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <form onSubmit={add} noValidate>
        <div className="field">
          <label htmlFor="supporter-name">Σε ποιον θέλεις να δώσεις πρόσβαση;</label>
          <input id="supporter-name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off"
            aria-invalid={!!error} aria-describedby={error ? "supporter-error" : undefined} />
          {error && <p id="supporter-error" className="field-error" role="alert">{error}</p>}
        </div>
        <div className="actions">
          <button type="submit" className="btn btn-primary">
            <UserRound aria-hidden="true" />
            Δώσε πρόσβαση
          </button>
        </div>
      </form>
    </Screen>
  );
}

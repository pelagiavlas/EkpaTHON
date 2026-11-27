import { useNavigate } from "react-router-dom";
import { BookOpen } from "lucide-react";
import { Screen } from "../components/Screen";

export function NotFound() {
  const navigate = useNavigate();
  return (
    <Screen title="Δεν βρήκαμε αυτή τη σελίδα" back="/">
      <p>Ίσως ο σύνδεσμος δεν ισχύει πια.</p>
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={() => navigate("/")}>
          <BookOpen aria-hidden="true" />
          Πήγαινε στα μαθήματά μου
        </button>
      </div>
    </Screen>
  );
}

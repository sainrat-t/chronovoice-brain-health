import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { NewPerson } from "./pages/NewPerson";
import { NewSession } from "./pages/NewSession";
import { PeopleList } from "./pages/PeopleList";
import { PersonPage } from "./pages/PersonPage";
import { ReportPage } from "./pages/ReportPage";
import { SessionPage } from "./pages/SessionPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<PeopleList />} />
        <Route path="people/new" element={<NewPerson />} />
        <Route path="people/:personId" element={<PersonPage />} />
        <Route path="people/:personId/new-session" element={<NewSession />} />
        <Route path="people/:personId/report" element={<ReportPage />} />
        <Route path="sessions/:sessionId" element={<SessionPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

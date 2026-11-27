import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useSettings } from "./settings";
import { Welcome } from "./screens/Welcome";
import { Courses, NewCourse } from "./screens/Courses";
import { ChangeLevel, CourseScreen, DeleteCourse } from "./screens/Course";
import { StartLevel, UploadScreen } from "./screens/Upload";
import { ChapterScreen } from "./screens/Chapter";
import { StudyScreen } from "./screens/Study";
import { QuestionsScreen } from "./screens/Questions";
import { ProgressScreen, SharedProgress } from "./screens/Progress";
import { SettingsColors, SettingsHome, SettingsMotion, SettingsSound, SettingsText } from "./screens/Settings";
import { SupporterScreen } from "./screens/Supporter";
import { AccessibilityStatement } from "./screens/Statement";
import { NotFound } from "./screens/NotFound";

const OPEN_WITHOUT_ONBOARDING = ["/welcome", "/shared", "/accessibility"];

export function App() {
  const { settings, loaded } = useSettings();
  const { pathname } = useLocation();
  const needsWelcome = loaded && !settings.onboarded && !OPEN_WITHOUT_ONBOARDING.some((p) => pathname.startsWith(p));

  return (
    <>
      <a className="skip-link" href="#main">
        Πήγαινε στο κύριο περιεχόμενο
      </a>
      {needsWelcome ? (
        <Navigate to="/welcome" replace />
      ) : (
        <Routes>
          <Route path="/welcome" element={<Welcome />} />
          <Route path="/" element={<Courses />} />
          <Route path="/courses/new" element={<NewCourse />} />
          <Route path="/courses/:id" element={<CourseScreen />} />
          <Route path="/courses/:id/upload" element={<UploadScreen />} />
          <Route path="/courses/:id/level" element={<ChangeLevel />} />
          <Route path="/courses/:id/delete" element={<DeleteCourse />} />
          <Route path="/chapters/:id/start" element={<StartLevel />} />
          <Route path="/chapters/:id" element={<ChapterScreen />} />
          <Route path="/sections/:id" element={<StudyScreen />} />
          <Route path="/sections/:id/questions" element={<QuestionsScreen />} />
          <Route path="/progress" element={<ProgressScreen />} />
          <Route path="/settings" element={<SettingsHome />} />
          <Route path="/settings/text" element={<SettingsText />} />
          <Route path="/settings/colors" element={<SettingsColors />} />
          <Route path="/settings/sound" element={<SettingsSound />} />
          <Route path="/settings/motion" element={<SettingsMotion />} />
          <Route path="/settings/supporter" element={<SupporterScreen />} />
          <Route path="/shared/:token" element={<SharedProgress />} />
          <Route path="/accessibility" element={<AccessibilityStatement />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      )}
    </>
  );
}

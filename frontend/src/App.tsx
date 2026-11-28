import { Route, Routes } from "react-router-dom";
import { Courses, NewCourse } from "./screens/Courses";
import { CourseScreen, DeleteCourse } from "./screens/Course";
import { UploadScreen } from "./screens/Upload";
import { ChapterScreen } from "./screens/Chapter";
import { ChangeLevel, StudyScreen } from "./screens/Study";
import { QuestionsScreen } from "./screens/Questions";
import { ExamScreen } from "./screens/Exam";
import { ProgressScreen, SharedProgress } from "./screens/Progress";
import { SettingsColors, SettingsHome, SettingsMotion, SettingsSound, SettingsText } from "./screens/Settings";
import { SupporterScreen } from "./screens/Supporter";
import { AccessibilityStatement } from "./screens/Statement";
import { NotFound } from "./screens/NotFound";

// No questions and no test before first use: the app opens straight on the courses.
export function App() {
  return (
    <>
      <a className="skip-link" href="#main">
        Πήγαινε στο κύριο περιεχόμενο
      </a>
      <Routes>
        <Route path="/" element={<Courses />} />
        <Route path="/courses/new" element={<NewCourse />} />
        <Route path="/courses/:id" element={<CourseScreen />} />
        <Route path="/courses/:id/upload" element={<UploadScreen />} />
        <Route path="/courses/:id/delete" element={<DeleteCourse />} />
        <Route path="/chapters/:id" element={<ChapterScreen />} />
        <Route path="/sections/:id" element={<StudyScreen />} />
        <Route path="/sections/:id/level" element={<ChangeLevel />} />
        <Route path="/sections/:id/questions" element={<QuestionsScreen />} />
        <Route path="/sections/:id/exam" element={<ExamScreen />} />
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
    </>
  );
}

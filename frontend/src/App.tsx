import { Route, Routes } from "react-router";
import DemoPage from "./pages/demo";
import MainLayout from "./layouts/MainLayout";
import HomePage from "./pages/home";
import LivePage from "./pages/live";
import ReportPage from "./pages/report";
import CasePage from "./pages/case";
import AdhocSearchPage from "./pages/adhoc";
import AdhocResultPage from "./pages/adhoc/result";
import AdhocLayout from "./layouts/AdhocLayout";
import ErrorBoundary from "./components/ErrorBoundary";

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<MainLayout />}>
          <Route
            index
            element={
              <ErrorBoundary>
                <HomePage />
              </ErrorBoundary>
            }
          />
          <Route path="live-detection" element={<LivePage />} />
          <Route path="adhoc" element={<AdhocLayout />}>
            <Route index element={<AdhocSearchPage />} />
            <Route path="result" element={<AdhocResultPage />} />
          </Route>
          <Route path="report" element={<ReportPage />} />
          <Route path="case" element={<CasePage />} />
        </Route>
        <Route path="demo" element={<DemoPage />} />
      </Routes>
    </ErrorBoundary>
  );
}

export default App;

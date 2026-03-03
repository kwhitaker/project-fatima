import { lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import RequireAuth from "./components/RequireAuth";
import Login from "./routes/Login";
import ResetPassword from "./routes/ResetPassword";
import Games from "./routes/Games";
import GameRoom from "./routes/GameRoom";

const DevPlayground = import.meta.env.DEV
  ? lazy(() => import("./routes/DevPlayground"))
  : null;

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route
          path="/games"
          element={
            <RequireAuth>
              <Games />
            </RequireAuth>
          }
        />
        <Route
          path="/g/:gameId"
          element={
            <RequireAuth>
              <GameRoom />
            </RequireAuth>
          }
        />
        {DevPlayground && (
          <Route path="/dev/playground" element={<DevPlayground />} />
        )}
        <Route path="*" element={<Navigate to="/games" replace />} />
      </Routes>
    </AuthProvider>
  );
}

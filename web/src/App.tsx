import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./routes/Login";
import Games from "./routes/Games";
import GameRoom from "./routes/GameRoom";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/games" element={<Games />} />
      <Route path="/g/:gameId" element={<GameRoom />} />
      <Route path="*" element={<Navigate to="/games" replace />} />
    </Routes>
  );
}

import { useParams } from "react-router-dom";

export default function GameRoom() {
  const { gameId } = useParams<{ gameId: string }>();

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold">Game {gameId}</h1>
      <p className="text-muted-foreground mt-2 text-sm">Loading game…</p>
    </div>
  );
}

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export default function Games() {
  const { signOut } = useAuth();

  return (
    <div className="container py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Games</h1>
        <div className="flex gap-2">
          <Button>Create Game</Button>
          <Button variant="outline" onClick={() => void signOut()}>
            Log out
          </Button>
        </div>
      </div>
      <p className="text-muted-foreground text-sm">No games yet.</p>
    </div>
  );
}

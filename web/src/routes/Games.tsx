import { Button } from "@/components/ui/button";

export default function Games() {
  return (
    <div className="container py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Games</h1>
        <Button>Create Game</Button>
      </div>
      <p className="text-muted-foreground text-sm">No games yet.</p>
    </div>
  );
}

import { Button } from "@/components/ui/button";

export default function Login() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm space-y-6 p-6">
        <h1 className="text-2xl font-bold">Sign in</h1>
        <p className="text-muted-foreground text-sm">
          Enter your email to receive a magic link.
        </p>
        <form className="space-y-4">
          <input
            type="email"
            placeholder="you@example.com"
            className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
          />
          <Button type="submit" className="w-full">
            Send magic link
          </Button>
        </form>
      </div>
    </div>
  );
}

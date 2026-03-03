import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

type Mode = "signin" | "signup" | "forgot";

export default function Login() {
  const { session, signIn, signUp, resetPasswordForEmail } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (session) navigate("/games", { replace: true });
  }, [session, navigate]);

  // Reset status when switching modes
  const switchMode = (next: Mode) => {
    setMode(next);
    setStatus("idle");
    setErrorMsg("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("sending");

    let error: Error | null = null;

    if (mode === "signin") {
      ({ error } = await signIn(email, password));
    } else if (mode === "signup") {
      ({ error } = await signUp(email, password));
      if (!error) setStatus("done"); // may need email confirmation
    } else {
      ({ error } = await resetPasswordForEmail(email));
      if (!error) setStatus("done");
    }

    if (error) {
      setStatus("error");
      setErrorMsg(error.message);
    }
  };

  const titles: Record<Mode, string> = {
    signin: "Sign in",
    signup: "Create account",
    forgot: "Reset password",
  };

  const doneMessages: Record<Mode, string> = {
    signin: "",
    signup: "Check your email to confirm your account, then sign in.",
    forgot: "Check your email for a password reset link.",
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <motion.div
        className="w-full max-w-sm space-y-6 p-6"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <h1 className="text-2xl font-bold">{titles[mode]}</h1>

        {status === "done" ? (
          <div className="space-y-4">
            <p className="text-sm text-green-600 dark:text-green-400">{doneMessages[mode]}</p>
            <button
              className="text-sm underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              onClick={() => switchMode("signin")}
            >
              Back to sign in
            </button>
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="border-input bg-background w-full rounded-none border-2 px-3 py-2 text-sm transition-colors hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary"
            />
            {mode !== "forgot" && (
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="border-input bg-background w-full rounded-none border-2 px-3 py-2 text-sm transition-colors hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary"
              />
            )}
            <Button type="submit" className="w-full" disabled={status === "sending"}>
              {status === "sending"
                ? "Please wait…"
                : mode === "signin"
                  ? "Sign in"
                  : mode === "signup"
                    ? "Create account"
                    : "Send reset link"}
            </Button>
            {status === "error" && (
              <p className="text-sm text-red-600 dark:text-red-400">{errorMsg}</p>
            )}
          </form>
        )}

        <div className="flex flex-col gap-1 text-sm text-center">
          {mode === "signin" && (
            <>
              <button className="text-accent underline hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded" onClick={() => switchMode("signup")}>
                Create an account
              </button>
              <button className="text-accent underline hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded" onClick={() => switchMode("forgot")}>
                Forgot password?
              </button>
            </>
          )}
          {mode !== "signin" && (
            <button className="text-accent underline hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded" onClick={() => switchMode("signin")}>
              Back to sign in
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}

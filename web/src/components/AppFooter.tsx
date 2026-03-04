export function AppFooter() {
  return (
    <footer className="border-t border-border bg-muted/20">
      <div className="container py-2">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[11px] leading-tight text-muted-foreground">
            Fan-made. Not affiliated with or endorsed by Wizards of the Coast or Square Enix.
            Dungeons &amp; Dragons and Curse of Strahd are trademarks of Wizards of the Coast.
            Final Fantasy and Triple Triad are trademarks of Square Enix.
            All trademarks belong to their respective owners.
          </p>
          <a
            className="text-[11px] underline underline-offset-2 text-accent hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            href="https://github.com/kwhitaker/project-fatima"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}

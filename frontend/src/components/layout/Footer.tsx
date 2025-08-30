'use client';

export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 mt-auto">
      <div className="container flex h-16 items-center justify-center px-4">
        <p className="text-sm text-muted-foreground text-center">
          Powered by{" "}
          <span className="font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            OpenProbe AI
          </span>
          {" "}• Built with Next.js & FastAPI
        </p>
      </div>
    </footer>
  );
}

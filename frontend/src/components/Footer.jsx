export default function Footer() {
  return (
    <footer className="border-t border-white/5">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10 text-sm text-mute sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-amber text-ink">
            <span className="block h-2 w-2 rounded-full bg-ink" />
          </span>
          <span className="font-display text-cream">Greenroom</span>
        </div>
        <p>Built for people getting ready to walk into the room.</p>
        <p>&copy; {new Date().getFullYear()} Greenroom. All rights reserved.</p>
      </div>
    </footer>
  );
}

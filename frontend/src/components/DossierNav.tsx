interface NavItem {
  id: string;
  label: string;
}

export function DossierNav({ items }: { items: NavItem[] }) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.history.replaceState(null, "", `#${id}`);
  };

  return (
    <nav
      aria-label="Dossier sections"
      className="sticky top-0 z-10 -mx-6 px-6 py-2 mb-8 bg-ink-900/95 backdrop-blur border-b border-ink-600 overflow-x-auto"
    >
      <ul className="flex items-center gap-4 min-w-max">
        {items.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              onClick={(e) => handleClick(e, item.id)}
              className="font-mono text-[10px] uppercase tracking-widest text-paper-faint hover:text-signal transition-colors whitespace-nowrap"
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

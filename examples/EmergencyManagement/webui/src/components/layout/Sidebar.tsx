import { NavLink } from 'react-router-dom';

interface NavItem {
  to: string;
  label: string;
}

const NAV_LINKS: NavItem[] = [
  { to: '/', label: 'Dashboard' },
  { to: '/messages', label: 'Emergency Action Messages' },
  { to: '/events', label: 'Events' },
];

export function Sidebar(): JSX.Element {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-title">Emergency Management</h1>
      </div>
      <nav className="sidebar-nav">
        {NAV_LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' sidebar-link-active' : ''}`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

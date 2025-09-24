import { NavLink } from 'react-router-dom';

import type { LucideIcon } from 'lucide-react';
import {
  CalendarDays,
  LayoutDashboard,
  MessagesSquare,
  RadioTower,
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

const NAV_LINKS: NavItem[] = [
  {
    to: '/messages',
    label: 'Action Messages',
    description: 'Create and dispatch emergency bulletins',
    icon: MessagesSquare,
  },
  {
    to: '/events',
    label: 'Events',
    description: 'Coordinate drills and live incidents',
    icon: CalendarDays,
  },
  {
    to: '/dashboard',
    label: 'Dashboard',
    description: 'Monitor gateway and network health',
    icon: LayoutDashboard,
  },
];

export function Sidebar(): JSX.Element {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo__mark">
            <RadioTower size={24} strokeWidth={2.5} aria-hidden="true" />
          </div>
          <div className="sidebar-logo__text">
            <span className="sidebar-logo__title">Emergency Ops</span>
            <span className="sidebar-logo__subtitle">Rapid Mesh Response</span>
          </div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {NAV_LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/messages'}
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' sidebar-link-active' : ''}`
            }
          >
            <span className="sidebar-link__icon" aria-hidden="true">
              <link.icon size={20} strokeWidth={2.2} />
            </span>
            <span className="sidebar-link__content">
              <span className="sidebar-link__label">{link.label}</span>
              <span className="sidebar-link__description">{link.description}</span>
            </span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

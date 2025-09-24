import { Navigate, createBrowserRouter } from 'react-router-dom';

import { Layout } from '../components/layout/Layout';
import { DashboardPage } from '../pages/DashboardPage';
import { EmergencyActionMessagesPage } from '../pages/EmergencyActionMessages/EmergencyActionMessagesPage';
import { EventsPage } from '../pages/Events/EventsPage';

export const routes = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="messages" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'messages',
        element: <EmergencyActionMessagesPage />,
      },
      {
        path: 'events',
        element: <EventsPage />,
      },
    ],
  },
];

export const router = createBrowserRouter(routes);

import { createBrowserRouter } from 'react-router-dom';

import { Layout } from '../components/layout/Layout';
import { DashboardPage } from '../pages/DashboardPage';
import { EmergencyActionMessagesPage } from '../pages/EmergencyActionMessagesPage';
import { EventsPage } from '../pages/EventsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
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
]);

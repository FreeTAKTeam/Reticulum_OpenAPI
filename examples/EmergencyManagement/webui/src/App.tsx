import { RouterProvider } from 'react-router-dom';

import { ToastProvider } from './components/toast';
import { router } from './router';

function App(): JSX.Element {
  return (
    <ToastProvider>
      <RouterProvider router={router} />
    </ToastProvider>
  );
}

export default App;

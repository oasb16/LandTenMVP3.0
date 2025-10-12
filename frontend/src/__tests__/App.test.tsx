import { render } from '@testing-library/react';
import Home from '../pages/index';

test('renders welcome message', () => {
  const { getByText } = render(<Home />);
  expect(getByText('Welcome to LandTenMVP3.0 Frontend')).toBeInTheDocument();
});
